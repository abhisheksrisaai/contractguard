"""
ContractGuard - Day 1 Tests
Verify PDF extraction, clause segmentation, and LLM connectivity.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure backend/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.pdf_extractor import PDFExtractor
from app.services.llm_service import ContractAnalyzer
from app.core.config import settings

# ── Sample contract text for testing (mock PDF content) ───────────────

SAMPLE_CONTRACT = """
CONSULTING SERVICES AGREEMENT

1. Services. Consultant agrees to provide software development services as described in
Exhibit A attached hereto. All services shall be performed in a professional and
workmanlike manner consistent with industry standards.

ARTICLE 2 — COMPENSATION
2.1 Fees. Client shall pay Consultant a fixed fee of $15,000 per month, payable
within thirty (30) days of receipt of an undisputed invoice.
2.2 Late Payment. Any payment not received within 45 days shall accrue interest at
the rate of 1.5% per month, compounded monthly.

SECTION 3 — TERMINATION
3.1 Termination for Convenience. Either party may terminate this Agreement at any
time, for any reason or no reason, upon fifteen (15) days written notice to the
other party.
3.2 Effect of Termination. Upon termination, Consultant shall immediately cease all
work and deliver all work product to Client.

4. CONFIDENTIALITY
4.1 Definition. "Confidential Information" means any non-public information disclosed
by one party to the other, whether orally or in writing.
4.2 Obligations. Each party agrees to hold Confidential Information in strict
confidence and not to disclose it to any third party without prior written consent.

5. LIMITATION OF LIABILITY
5.1 IN NO EVENT SHALL CONSULTANT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL,
OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, EVEN IF ADVISED.
5.2 Consultant's total liability under this Agreement shall not exceed the fees
paid by Client during the six (6) months preceding the claim.

6. GOVERNING LAW. This Agreement shall be governed by the laws of the State of
Delaware, without regard to its conflict of laws principles.

7. INTELLECTUAL PROPERTY. All work product created by Consultant in the course of
performing the Services shall be owned exclusively by Client upon full payment.
Consultant hereby assigns all rights, title, and interest in such work product.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date below.
"""


# ── PDF Extractor Tests ────────────────────────────────────────────────

class TestPDFExtractor:
    """Tests for PDFExtractor — text extraction and clause segmentation."""

    @classmethod
    def setup_class(cls):
        cls.extractor = PDFExtractor()

    def test_extract_text_file_not_found(self):
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            self.extractor.extract_text("/nonexistent/path/file.pdf")

    def test_extract_text_non_pdf(self):
        """Should raise ValueError for non-PDF files."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not a pdf")
            f.flush()
            with pytest.raises(ValueError, match="not a PDF"):
                self.extractor.extract_text(f.name)
            os.unlink(f.name)

    def test_extract_text_from_pdf(self):
        """Should extract text from a real (generated) PDF."""
        # Create a minimal valid PDF with PyMuPDF
        pdf_path = _create_test_pdf(SAMPLE_CONTRACT)
        try:
            text = self.extractor.extract_text(pdf_path)
            assert isinstance(text, str)
            assert len(text) > 100
            assert "CONSULTING SERVICES" in text
            assert "GOVERNING LAW" in text
        finally:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)

    def test_segment_clauses(self):
        """Should segment text into multiple typed clauses."""
        clauses = self.extractor.segment_clauses(SAMPLE_CONTRACT)
        assert isinstance(clauses, list)
        assert len(clauses) >= 2, f"Expected at least 2 clauses, got {len(clauses)}"

        # Each clause should have required keys
        for clause in clauses:
            assert "id" in clause
            assert "title" in clause
            assert "content" in clause
            assert "type" in clause
            assert isinstance(clause["id"], str)
            assert isinstance(clause["content"], str)
            assert len(clause["content"]) > 10, f"Clause {clause['id']} too short"

        # Check that clause types are valid
        valid_types = [
            "payment", "termination", "liability", "confidentiality",
            "intellectual_property", "data_protection", "non_compete",
            "governing_law", "force_majeure", "warranty", "general",
        ]
        for clause in clauses:
            assert clause["type"] in valid_types, f"Invalid type: {clause['type']}"

    def test_classify_clause_type(self):
        """Should correctly classify payment and termination clauses."""
        assert self.extractor.classify_clause_type("Payment", "Client shall pay a fee of $100") == "payment"
        assert self.extractor.classify_clause_type("Termination", "Either party may terminate") == "termination"
        assert self.extractor.classify_clause_type("", "confidential non-disclosure obligation") == "confidentiality"
        assert self.extractor.classify_clause_type("Unknown", "something unrelated") == "general"

    def test_segment_empty_text(self):
        """Should handle empty/mostly-empty text gracefully."""
        clauses = self.extractor.segment_clauses("")
        assert len(clauses) >= 0
        # Even for empty text, it should return a valid list
        assert isinstance(clauses, list)

    def test_segment_very_short_text(self):
        """Should handle very short text."""
        clauses = self.extractor.segment_clauses("Short.")
        assert isinstance(clauses, list)


# ── LLM Service Tests ──────────────────────────────────────────────────

class TestLLMService:
    """Tests for ContractAnalyzer — requires a valid GROQ_API_KEY."""

    @classmethod
    def setup_class(cls):
        cls.analyzer = ContractAnalyzer()

    def test_groq_ping(self):
        """Should successfully call Groq API and get a response."""
        try:
            response = self.analyzer._call_groq(
                system="You are a helpful assistant. Respond with a single word: 'pong'.",
                user_message="ping",
                temperature=0.0,
                max_tokens=10,
            )
            assert isinstance(response, str)
            assert len(response) > 0
            # Should contain "pong" (case-insensitive)
            assert "pong" in response.lower() or "pong" in response.lower(), f"Unexpected: {response}"
        except RuntimeError as e:
            pytest.skip(f"Groq API unavailable (check GROQ_API_KEY): {e}")

    def test_analyze_clause_returns_required_keys(self):
        """Should return all required keys for a clause analysis."""
        clause = {
            "id": "test_001",
            "title": "Late Payment Clause",
            "content": "Interest at 1.5% per month shall accrue on any overdue payment.",
            "type": "payment",
        }
        try:
            result = self.analyzer.analyze_clause(clause)
            required = [
                "risk_level", "risk_score", "risk_factors",
                "explanation", "suggested_alternative", "missing_protections",
            ]
            for key in required:
                assert key in result, f"Missing key: {key}"
            assert result["risk_level"] in ("Low", "Medium", "High")
            assert 0 <= result["risk_score"] <= 100
            assert isinstance(result["risk_factors"], list)
        except RuntimeError as e:
            pytest.skip(f"Groq API unavailable: {e}")

    def test_analyze_contract_aggregation(self):
        """Should aggregate clause results into overall report."""
        clauses = [
            {"id": "c1", "risk_level": "High", "risk_score": 85},
            {"id": "c2", "risk_level": "Low", "risk_score": 10},
            {"id": "c3", "risk_level": "Medium", "risk_score": 50},
        ]
        report = self.analyzer.analyze_contract(clauses)
        assert "overall_score" in report
        assert "risk_breakdown" in report
        assert "high_risk_clauses" in report
        assert "summary" in report
        assert report["risk_breakdown"]["High"] == 1
        assert report["risk_breakdown"]["Medium"] == 1
        assert report["risk_breakdown"]["Low"] == 1
        assert isinstance(report["overall_score"], (int, float))

    def test_analyze_contract_empty(self):
        """Should handle empty clause list."""
        report = self.analyzer.analyze_contract([])
        assert report["overall_score"] == 0
        assert report.get("total_clauses", 0) == 0

    def test_answer_question_basic(self):
        """Should answer a simple contract question."""
        contract = "Consultant shall be paid $15,000 per month. Either party may terminate with 15 days notice."
        try:
            answer = self.analyzer.answer_question(contract, "What is the notice period?")
        except RuntimeError as e:
            pytest.skip(f"Groq API unavailable: {e}")

        # If Groq key missing, answer_question returns error string — skip
        if "couldn't answer" in answer.lower() or "GROQ_API_KEY" in answer:
            pytest.skip("Groq API key not configured")

        assert isinstance(answer, str)
        assert len(answer) > 0
        # Should mention 15 days
        assert "15" in answer

    def test_json_parsing_clean(self):
        """Should parse clean JSON."""
        raw = '{"risk_level": "High", "risk_score": 80, "risk_factors": ["A", "B"]}'
        result = self.analyzer._parse_json(raw)
        assert result["risk_level"] == "High"
        assert result["risk_score"] == 80

    def test_json_parsing_with_fences(self):
        """Should strip markdown code fences."""
        raw = '```json\n{"risk_level": "Low", "risk_score": 10}\n```'
        result = self.analyzer._parse_json(raw)
        assert result["risk_level"] == "Low"

    def test_json_parsing_malformed(self):
        """Should extract fields heuristically from malformed output."""
        raw = 'risk_level: "Medium" risk_score: 42 explanation: "Some risk"'
        result = self.analyzer._parse_json(raw)
        assert "risk_level" in result
        assert "risk_score" in result


# ── Config Tests ───────────────────────────────────────────────────────

class TestConfig:
    """Tests for application configuration."""

    def test_settings_loads(self):
        """Should load settings with defaults."""
        assert settings.LLM_PROVIDER == "groq"
        assert settings.APP_PORT == 8000
        assert settings.MAX_UPLOAD_SIZE_MB == 10

    def test_settings_has_paths(self):
        """Should provide path properties."""
        assert settings.project_root.exists()
        assert settings.upload_dir.exists()
        assert settings.reports_dir.exists()

    def test_validate_groq_key_missing(self):
        """Should raise if key is the placeholder."""
        original = settings.GROQ_API_KEY
        settings.GROQ_API_KEY = "your_groq_api_key_here"
        with pytest.raises(ValueError, match="GROQ_API_KEY"):
            settings.validate_groq_key()
        settings.GROQ_API_KEY = original


# ── Helpers ─────────────────────────────────────────────────────────────

def _create_test_pdf(text: str) -> str:
    """Create a temporary PDF file from text and return its path."""
    import fitz  # PyMuPDF

    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    doc = fitz.open()
    page = doc.new_page()
    # Use insert_textbox to fit within page margins
    rect = fitz.Rect(50, 50, 550, 800)
    page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    doc.save(path)
    doc.close()
    return path


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
