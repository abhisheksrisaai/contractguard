"""
ContractGuard - PDF Extraction & Clause Segmentation Service

Handles:
- Extracting raw text from PDF contracts (PyMuPDF + pdfplumber fallback)
- Segmenting extracted text into logical clauses
- Classifying each clause by type (payment, termination, liability, etc.)
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


# ── Clause type patterns for regex-based classification ──────────────
# Used as a fallback when the LLM is unavailable or for quick pre-classification.
CLAUSE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "payment": [
        "payment", "fee", "compensation", "invoice", "price", "amount due",
        "remuneration", "pay", "paid", "billing", "consideration",
    ],
    "termination": [
        "termination", "cancel", "end of agreement", "notice period",
        "terminate", "dissolution", "wind up",
    ],
    "liability": [
        "liability", "indemnification", "indemnify", "hold harmless",
        "damages", "loss", "cap on liability", "limitation of liability",
    ],
    "confidentiality": [
        "confidential", "non-disclosure", "nda", "proprietary information",
        "trade secret", "confidentiality obligation",
    ],
    "intellectual_property": [
        "intellectual property", "ip rights", "copyright", "patent",
        "trademark", "ownership", "license grant", "moral rights",
    ],
    "data_protection": [
        "data protection", "personal data", "gdpr", "privacy",
        "data processing", "data breach", "data subject",
    ],
    "non_compete": [
        "non-compete", "non-solicitation", "restrictive covenant",
        "non-competition", "no poaching", "non-solicit",
    ],
    "governing_law": [
        "governing law", "jurisdiction", "venue", "arbitration",
        "dispute resolution", "choice of law", "forum",
    ],
    "force_majeure": [
        "force majeure", "act of god", "unforeseeable", "beyond control",
        "natural disaster", "pandemic", "epidemic",
    ],
    "warranty": [
        "warranty", "representation", "warrants", "guarantee",
        "as is", "fitness for purpose", "merchantability",
    ],
}


class PDFExtractor:
    """
    Extracts text from PDF contracts and segments it into logical clauses.

    Uses PyMuPDF as the primary extraction engine with pdfplumber as a
    fallback for complex layouts. Handles scanned PDFs gracefully by
    returning whatever text is available (OCR to be added later).
    """

    # ── Clause boundary patterns ──────────────────────────────────────
    # Headers like "1.", "ARTICLE 2", "Section 3.1", "Clause IV", etc.
    CLAUSE_HEADER_RE = re.compile(
        r"(?:^|\n)"                          # start of line
        r"\s*"                               # optional whitespace
        r"(?:"                               # begin header group
        r"(?:Article|Section|Clause|PART|SECTION|ARTICLE)\s+\d+"  # Article 1
        r"|"                                 # or
        r"(?:ARTICLE|SECTION|CLAUSE)\s+\d+"  # ARTICLE 1
        r"|"                                 # or
        r"\d+[\.\)]\s+"                      # 1. or 1)
        r"|"                                 # or
        r"[IVX]+\.\s+"                       # IV.
        r")"                                 # end header group
        r"\s*"                               # optional whitespace
        r"[A-Z]"                             # followed by uppercase letter
    )

    # Secondary pattern: ALL-CAPS short line followed by body text
    ALL_CAPS_HEADER_RE = re.compile(
        r"(?:^|\n)([A-Z][A-Z\s]{10,80})(?:\n|$)"
    )

    def extract_text(self, file_path: str) -> str:
        """
        Extract raw text from a PDF file.

        Args:
            file_path: Absolute or relative path to PDF file.

        Returns:
            Extracted text as a single string.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is not a valid PDF or contains no extractable text.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        if not path.suffix.lower() == ".pdf":
            raise ValueError(f"File is not a PDF: {file_path}")

        logger.info("Extracting text from: %s", path.name)

        text_blocks: List[str] = []

        try:
            doc = fitz.open(str(path))

            if len(doc) == 0:
                raise ValueError("PDF contains 0 pages.")

            for page_num, page in enumerate(doc, start=1):
                page_text = page.get_text("text")
                if page_text.strip():
                    text_blocks.append(page_text.strip())
                else:
                    logger.warning("Page %d produced no text (may be scanned image).", page_num)

            doc.close()

        except Exception as exc:
            logger.error("PyMuPDF failed: %s. Attempting pdfplumber fallback.", exc)
            text_blocks = self._fallback_pdfplumber(path)
            if not text_blocks:
                raise ValueError(
                    f"Could not extract text from {path.name}. "
                    f"The PDF may be image-only (scanned). OCR support is planned."
                ) from exc

        full_text = "\n\n".join(text_blocks)

        if not full_text.strip():
            raise ValueError(f"No extractable text found in {path.name}.")

        logger.info("Extracted %d characters from %d page(s).", len(full_text), len(text_blocks))
        return full_text

    def _fallback_pdfplumber(self, path: Path) -> List[str]:
        """Secondary extraction using pdfplumber for tricky layouts."""
        try:
            import pdfplumber

            blocks: List[str] = []
            with pdfplumber.open(str(path)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        blocks.append(text.strip())
            return blocks
        except Exception as exc:
            logger.warning("pdfplumber fallback also failed: %s", exc)
            return []

    # ── Clause Segmentation ───────────────────────────────────────────

    def segment_clauses(self, text: str) -> List[Dict]:
        """
        Segment raw contract text into logical clauses.

        Strategy:
        1. First attempt: split on numbered/article headers (e.g. "1.", "Article 2").
        2. Fallback: split on double-newlines (paragraph boundaries).
        3. Merge very short segments with neighbors.
        4. Classify each clause type.

        Args:
            text: Raw contract text from extract_text().

        Returns:
            List of clause dicts with keys: id, title, content, type.
        """
        logger.info("Segmenting text into clauses (%d chars)...", len(text))

        raw_clauses = self._split_by_headers(text)

        if len(raw_clauses) < 2:
            logger.info("Header-based split produced only %d clause(s). Falling back to paragraph split.", len(raw_clauses))
            raw_clauses = self._split_by_paragraphs(text)

        # Merge short fragments into neighbors
        merged = self._merge_short_clauses(raw_clauses, min_length=100)

        # Build final structured list
        clauses: List[Dict] = []
        for idx, raw in enumerate(merged, start=1):
            title = self._extract_title(raw)
            body = self._clean_body(raw, title)
            ctype = self.classify_clause_type(title, body)

            if not body.strip():
                continue  # skip empty clauses

            clauses.append({
                "id": f"clause_{idx:03d}",
                "title": title or f"Clause {idx}",
                "content": body,
                "type": ctype,
            })

        if not clauses:
            # Last resort: treat entire text as single clause
            clauses.append({
                "id": "clause_001",
                "title": "Entire Agreement",
                "content": text.strip(),
                "type": "general",
            })

        logger.info("Segmented into %d clauses.", len(clauses))
        return clauses

    def _split_by_headers(self, text: str) -> List[str]:
        """Split text using clause header regex."""
        # Find all header positions
        matches = list(self.CLAUSE_HEADER_RE.finditer(text))
        if not matches:
            return [text]

        segments: List[str] = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            segment = text[start:end].strip()
            segments.append(segment)

        # Prepend text before the first header as preamble (if substantial)
        if matches and matches[0].start() > 0:
            preamble = text[:matches[0].start()].strip()
            if len(preamble) > 50:
                segments.insert(0, preamble)

        return segments

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Fallback split: treat double-newlines as clause boundaries."""
        # Normalize line endings
        normalized = re.sub(r"\r\n|\r", "\n", text)
        # Split on blank lines
        parts = re.split(r"\n\s*\n", normalized)
        return [p.strip() for p in parts if p.strip() and len(p.strip()) > 20]

    def _merge_short_clauses(self, clauses: List[str], min_length: int = 100) -> List[str]:
        """Merge short segments into neighboring clauses to avoid orphan lines."""
        if not clauses:
            return []

        merged: List[str] = []
        buffer = ""

        for clause in clauses:
            if len(clause) < min_length:
                buffer += "\n" + clause if buffer else clause
            else:
                if buffer:
                    merged.append(buffer.strip())
                    buffer = ""
                merged.append(clause)

        if buffer:
            # Append remaining buffer to last clause (or make it standalone)
            if merged:
                merged[-1] += "\n" + buffer
            else:
                merged.append(buffer.strip())

        return merged

    def _extract_title(self, text: str) -> str:
        """Extract a human-readable title from the first line of a clause."""
        lines = text.strip().split("\n")
        if not lines:
            return ""

        first_line = lines[0].strip()

        # If first line is short and looks like a header, use it as title
        if len(first_line) <= 120 and re.search(r"[A-Z]{2,}|^\d+[\.\)]|Article|Section|Clause", first_line, re.IGNORECASE):
            return first_line

        # Otherwise take first ~85 chars as a summary title
        return first_line[:85] + ("..." if len(first_line) > 85 else "")

    def _clean_body(self, text: str, title: str) -> str:
        """Remove title from body text and strip excess whitespace."""
        body = text.strip()
        if title and body.startswith(title):
            body = body[len(title):].strip()
        # Collapse multiple spaces/newlines
        body = re.sub(r"\n{3,}", "\n\n", body)
        body = re.sub(r"[ \t]+", " ", body)
        return body.strip()

    # ── Clause Type Classification ────────────────────────────────────

    def classify_clause_type(self, title: str, content: str) -> str:
        """
        Classify a clause into one of the predefined types using keyword matching.

        Types: payment, termination, liability, confidentiality,
               intellectual_property, data_protection, non_compete,
               governing_law, force_majeure, warranty, general.

        Args:
            title: Clause title.
            content: Clause body content.

        Returns:
            Lowercase type string.
        """
        combined = (title + " " + content).lower()
        scores: Dict[str, int] = {}

        for ctype, keywords in CLAUSE_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                scores[ctype] = score

        if not scores:
            return "general"

        # Return the type with the most keyword matches
        best_type = max(scores, key=lambda k: scores[k])  # type: ignore[arg-type]
        return best_type
