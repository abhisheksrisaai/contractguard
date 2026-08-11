"""
ContractGuard - PDF Extraction & Clause Segmentation Service

Handles:
- Extracting raw text from PDF contracts (PyMuPDF + pdfplumber fallback)
- Detecting garbled/scanned PDFs with broken text layers
- Segmenting extracted text into logical clauses
- Classifying each clause by type (payment, termination, liability, etc.)
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


# ── Custom exception for scanned/garbled PDFs ───────────────────────

class ScannedPDFError(ValueError):
    """Raised when extracted text is garbled (scanned image with broken text layer)."""
    pass


# ── Clause type patterns for regex-based classification ──────────────
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
    fallback for complex layouts.
    """

    # ── Clause boundary patterns ──────────────────────────────────────
    # Matches numbered/article/schedule/lettered clause headers.
    # Covers: "1.", "1)", "2.1", "2.1.1" (decimal), "Article 2",
    # "SCHEDULE 1", "ANNEXURE A", "EXHIBIT B", "APPENDIX C",
    # "(a)", "(b)" lettered sub-clauses (start-of-line only),
    # Roman numerals "IV.", "VII." — all followed by any-case letter.
    #
    # Note: The trailing [\s\u2014\u2013\-\:\.]*[A-Za-z] handles em-dash
    # separators like "SCHEDULE 1 \u2014 Fees".
    CLAUSE_HEADER_RE = re.compile(
        r"(?:^|\n)"                              # start of line
        r"\s*"                                   # optional whitespace
        r"(?:"                                   # begin header group
        # Word-label headers: Article/Section/Clause/PART + number
        r"(?:Article|Section|Clause|PART|SECTION|ARTICLE)\s+\d+"
        r"|"
        # Schedule / Annexure / Exhibit / Appendix + identifier
        r"(?:Schedule|Annexure|Exhibit|Appendix|"
        r"SCHEDULE|ANNEXURE|EXHIBIT|APPENDIX)\s+[A-Za-z0-9]"
        r"|"
        # Decimal numbering: 2.1, 2.1.1, 2.1.1.1
        r"\d+\.\d+(?:\.\d+)*\s+"
        r"|"
        # Simple numbering: 1., 1)
        r"\d+[\.\)]\s+"
        r"|"
        # Roman numerals: IV., VII., X.
        r"[IVX]+\.\s+"
        r"|"
        # Lettered markers: (a), (b), (c) at start of line
        r"\([a-z]\)\s+"
        r")"
        # Separator (whitespace, em-dash, en-dash, hyphen, colon, period)
        r"[\s\u2014\u2013\-\:]*"
        r"[A-Za-z]"                              # followed by any-case letter
    )

    # Title-Case or ALL-CAPS standalone heading line.
    # Captures unnumbered headings like "DUTIES AND RESPONSIBILITIES" or
    # "Services and Deliverables" that are short (<80 chars),
    # no trailing period, and followed by a longer body paragraph.
    TITLE_CASE_HEADER_RE = re.compile(
        r"(?:^|\n)"                              # start of line
        r"("                                     # capture group 1: heading
        r"[A-Z][A-Za-z\s\-/,&]{4,75}"            # Title-Case / mixed
        r"|"
        r"[A-Z][A-Z\s\-/,&]{4,75}"               # ALL-CAPS
        r")"
        r"(?:\n|$)"                              # end of line
    )

    # ── Public API ────────────────────────────────────────────────────

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

        # ── Garbled text detection ──────────────────────────────
        if self.is_garbled(full_text):
            raise ScannedPDFError(
                "This PDF appears to be a scanned image with no readable text layer. "
                "Please upload a text-based PDF (exported from Word/Google Docs) "
                "or a higher-quality scan."
            )

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

    # ── Garbled Text Detection ─────────────────────────────────────

    PUNCTUATION_OK = set(".,;:!?()[]{}'\"-—–/\\&@#%*+=<>|~`$€£¥ ")  # noqa: E501

    @classmethod
    def is_garbled(cls, text: str) -> bool:
        """
        Detect scanned/garbled text with broken embedded text layers.

        Heuristics:
        (a) Alphanumeric + normal-punctuation ratio < 0.75
        (b) Word-like tokens (2+ letters) ratio < 0.5 of all tokens
        (c) Non-printable/special-char density > 15% of non-space chars

        Returns True if any heuristic fires (text is garbled).
        """
        if not text or len(text) < 100:
            return False  # too short to judge

        # Use a sample (first 5000 chars) for performance
        sample = text[:5000]

        # ── Heuristic (a): alphanumeric + ok-punctuation ratio ────
        good_chars = sum(1 for c in sample if c.isalnum() or c in cls.PUNCTUATION_OK or c == '\n')
        ratio_a = good_chars / max(len(sample), 1)

        # ── Heuristic (b): word-like token ratio ─────────────────
        tokens = sample.split()
        word_like = sum(1 for t in tokens if re.match(r'[A-Za-z]{2,}', t))
        ratio_b = word_like / max(len(tokens), 1)

        # ── Heuristic (c): special-char density ──────────────────
        non_space = [c for c in sample if c != ' ']
        if non_space:
            special = sum(
                1 for c in non_space
                if not c.isalnum() and c not in cls.PUNCTUATION_OK and c != '\n'
            )
            ratio_c = special / len(non_space)
        else:
            ratio_c = 0.0

        garbled = ratio_a < 0.75 or ratio_b < 0.5 or ratio_c > 0.15

        if garbled:
            logger.warning(
                "Garbled text detected — ratios: alphanum+ok=%.3f, wordlike=%.3f, special=%.3f",
                ratio_a, ratio_b, ratio_c,
            )

        return garbled

    # ── Clause Segmentation ───────────────────────────────────────────

    def segment_clauses(self, text: str) -> List[Dict]:
        """
        Segment raw contract text into logical clauses.

        Strategy:
        1. Find all header candidates (numbered, article, schedule, lettered,
           unnumbered Title-Case/ALL-CAPS headings).
        2. Split text at those header positions.
        3. Fallback: split on double-newlines if too few segments.
        4. Merge very short segments into neighbors (min_length=60).
        5. Classify each clause type.

        Args:
            text: Raw contract text from extract_text().

        Returns:
            List of clause dicts with keys: id, title, content, type.
        """
        logger.info("Segmenting text into clauses (%d chars)...", len(text))

        raw_clauses = self._split_by_headers(text)

        if len(raw_clauses) < 2:
            logger.info(
                "Header-based split produced only %d clause(s). "
                "Falling back to paragraph split.",
                len(raw_clauses),
            )
            raw_clauses = self._split_by_paragraphs(text)

        # Merge short fragments (min_length=60 accommodates short
        # commercial clauses that might otherwise be merged away)
        merged = self._merge_short_clauses(raw_clauses, min_length=60)

        # Build final structured list
        clauses: List[Dict] = []
        for idx, raw in enumerate(merged, start=1):
            title = self._extract_title(raw)
            body = self._clean_body(raw, title)
            ctype = self.classify_clause_type(title, body)

            if not body.strip():
                continue

            clauses.append({
                "id": f"clause_{idx:03d}",
                "title": title or f"Clause {idx}",
                "content": body,
                "type": ctype,
            })

        if not clauses:
            clauses.append({
                "id": "clause_001",
                "title": "Entire Agreement",
                "content": text.strip(),
                "type": "general",
            })

        logger.info("Segmented into %d clauses.", len(clauses))
        return clauses

    # ── Header Detection ─────────────────────────────────────────────

    def _find_all_header_positions(self, text: str) -> List[int]:
        """
        Find all potential clause boundary positions in text.

        Combines regex-based header matches (numbered, article, schedule,
        lettered) with unnumbered Title-Case/ALL-CAPS heading detection.
        Filters false positives (inline references, mid-paragraph caps).
        Returns sorted, deduplicated list of character positions.
        """
        positions: List[int] = []

        # ── Pass 1: Regex header matches ──────────────────────────
        for m in self.CLAUSE_HEADER_RE.finditer(text):
            pos = m.start()
            match_text = m.group(0).lstrip()

            # Filter: lettered markers "(a)" only valid if on a
            # short standalone line (< 70 chars) followed by a body
            if match_text.startswith("("):
                line = self._line_at(text, pos)
                if line is not None and len(line) >= 70:
                    # Long line → likely inline reference, skip
                    continue
                # Also skip if not followed by body paragraph
                following = self._line_after(text, pos, line)
                if following is None or len(following) < 20:
                    continue

            positions.append(pos)

        # ── Pass 2: Unnumbered Title-Case / ALL-CAPS headings ─────
        for m in self.TITLE_CASE_HEADER_RE.finditer(text):
            pos = m.start()
            heading = (m.group(1) or m.group(0)).strip()

            # Too short or too long → skip
            if len(heading) < 5 or len(heading) > 80:
                continue

            # Ends with period/colon → probably not a heading
            if heading.rstrip().endswith((".", ":")):
                continue

            # Skip if already near an existing regex-matched position
            if any(abs(pos - p) < len(heading) for p in positions):
                continue

            # Must be followed by a longer body line
            following = self._line_after(text, pos, heading)
            if following is None or len(following) < 30:
                continue

            # At least 50% of words must start with uppercase
            words = [w for w in heading.split() if len(w) > 1]
            if not words:
                continue
            caps_words = sum(1 for w in words if w[0].isupper())
            if caps_words < max(2, len(words) * 0.5):
                continue

            positions.append(pos)

        return sorted(set(positions))

    def _line_at(self, text: str, pos: int) -> Optional[str]:
        """Return the full line containing character position `pos`."""
        start = text.rfind("\n", 0, pos) + 1  # -1 → 0
        end = text.find("\n", pos)
        if end == -1:
            end = len(text)
        return text[start:end]

    def _line_after(self, text: str, pos: int, heading: str) -> Optional[str]:
        """Return the line immediately following `heading` at `pos`."""
        heading_end = pos + len(heading)
        nl = text.find("\n", heading_end)
        if nl == -1:
            return None
        next_start = nl + 1
        next_end = text.find("\n", next_start)
        if next_end == -1:
            next_end = len(text)
        return text[next_start:next_end].strip()

    def _split_by_headers(self, text: str) -> List[str]:
        """Split text using detected header positions."""
        positions = self._find_all_header_positions(text)
        if not positions:
            return [text]

        segments: List[str] = []
        for i, pos in enumerate(positions):
            start = pos
            end = positions[i + 1] if i + 1 < len(positions) else len(text)
            segment = text[start:end].strip()
            segments.append(segment)

        # Prepend text before the first header as preamble if substantial
        if positions and positions[0] > 0:
            preamble = text[:positions[0]].strip()
            if len(preamble) > 50:
                segments.insert(0, preamble)

        return segments

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Fallback split: treat double-newlines as clause boundaries."""
        normalized = re.sub(r"\r\n|\r", "\n", text)
        parts = re.split(r"\n\s*\n", normalized)
        return [p.strip() for p in parts if p.strip() and len(p.strip()) > 20]

    def _merge_short_clauses(self, clauses: List[str], min_length: int = 60) -> List[str]:
        """Merge short segments into neighboring clauses."""
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

        if len(first_line) <= 120 and re.search(
            r"[A-Z]{2,}|^\d+[\.\)]|Article|Section|Clause|"
            r"Schedule|Annexure|Exhibit|Appendix|^\([a-z]\)",
            first_line,
            re.IGNORECASE,
        ):
            return first_line

        return first_line[:85] + ("..." if len(first_line) > 85 else "")

    def _clean_body(self, text: str, title: str) -> str:
        """Remove title from body text and strip excess whitespace."""
        body = text.strip()
        if title and body.startswith(title):
            body = body[len(title):].strip()
        body = re.sub(r"\n{3,}", "\n\n", body)
        body = re.sub(r"[ \t]+", " ", body)
        return body.strip()

    # ── Clause Type Classification ────────────────────────────────────

    def classify_clause_type(self, title: str, content: str) -> str:
        """
        Classify a clause into one of the predefined types using keyword matching.
        """
        combined = (title + " " + content).lower()
        scores: Dict[str, int] = {}

        for ctype, keywords in CLAUSE_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > 0:
                scores[ctype] = score

        if not scores:
            return "general"

        return max(scores, key=lambda k: scores[k])  # type: ignore[arg-type]
