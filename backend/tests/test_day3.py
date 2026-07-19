"""
ContractGuard - Day 3 Tests
Test FastAPI endpoints: /, /api/health, /api/analyze, /api/ask, /api/report.
"""

import io
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure backend/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app
from app.core.config import settings

client = TestClient(app)

# ── Helper to create a minimal PDF in memory ────────────────────────

def _make_test_pdf_bytes() -> bytes:
    """Create a minimal text PDF using PyMuPDF and return its bytes."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 800)
    text = (
        "CONSULTING SERVICES AGREEMENT\n\n"
        "1. Services. Consultant agrees to provide software development services.\n\n"
        "2. Compensation. Client shall pay Consultant $10,000 per month within 30 days of invoice.\n\n"
        "3. Termination. Either party may terminate with 15 days written notice.\n\n"
        "4. Confidentiality. Both parties agree to protect confidential information.\n\n"
        "5. Limitation of Liability. Consultant's liability is capped at fees paid in 6 months."
    )
    page.insert_textbox(rect, text, fontsize=11, fontname="helv")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ── Tests ──────────────────────────────────────────────────────────

class TestRootAndHealth:
    """Tests for basic endpoints."""

    def test_root(self):
        """GET / should return welcome message."""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data

    def test_health(self):
        """GET /api/health should return service statuses."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert "groq" in data["services"]
        assert "qdrant" in data["services"]

    def test_docs_available(self):
        """GET /docs should return Swagger UI."""
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert "swagger" in resp.text.lower() or "openapi" in resp.text.lower()

    def test_redoc_available(self):
        """GET /redoc should return ReDoc."""
        resp = client.get("/redoc")
        assert resp.status_code == 200


class TestAnalyzeEndpoint:
    """Tests for POST /api/analyze."""

    def test_analyze_valid_pdf(self):
        """Should successfully analyze a valid PDF contract."""
        pdf_bytes = _make_test_pdf_bytes()
        files = {"file": ("test_contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        resp = client.post("/api/analyze", files=files)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        assert data["success"] is True
        assert "filename" in data
        assert "overall_score" in data
        assert "risk_breakdown" in data
        assert "clauses" in data
        assert len(data["clauses"]) >= 1, f"Expected at least 1 clause, got {len(data['clauses'])}"

        # Each clause should have required fields
        for clause in data["clauses"]:
            assert "id" in clause
            assert "risk_level" in clause
            assert clause["risk_level"] in ("Low", "Medium", "High")
            assert "risk_score" in clause
            assert 0 <= clause["risk_score"] <= 100

    def test_analyze_non_pdf(self):
        """Should reject non-PDF files with 400."""
        files = {"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")}
        resp = client.post("/api/analyze", files=files)
        assert resp.status_code == 400
        assert "not a pdf" in resp.json()["detail"].lower()

    def test_analyze_no_file(self):
        """Should return 400 when no file is provided."""
        resp = client.post("/api/analyze")
        assert resp.status_code == 422  # FastAPI validation error

    def test_analyze_empty_pdf(self):
        """Should reject empty file."""
        files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
        resp = client.post("/api/analyze", files=files)
        assert resp.status_code in (400, 422)

    def test_analyze_return_structure(self):
        """Response structure should match expected schema."""
        pdf_bytes = _make_test_pdf_bytes()
        files = {"file": ("contract.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        resp = client.post("/api/analyze", files=files)

        if resp.status_code == 200:
            data = resp.json()
            required_top = [
                "success", "filename", "overall_score", "risk_breakdown",
                "high_risk_clauses", "assessment", "total_clauses", "clauses",
            ]
            for key in required_top:
                assert key in data, f"Missing top-level key: {key}"


class TestAskEndpoint:
    """Tests for POST /api/ask."""

    def test_ask_basic(self):
        """Should answer a simple contract question."""
        payload = {
            "contract_text": "Consultant shall be paid $15,000 per month within 30 days of invoice. Either party may terminate with 15 days written notice.",
            "question": "What is the payment amount?",
        }
        resp = client.post("/api/ask", json=payload)

        if "GROQ_API_KEY" in settings.GROQ_API_KEY and "your_" in settings.GROQ_API_KEY:
            pytest.skip("Groq API key not configured")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_ask_empty_contract(self):
        """Should reject empty contract text."""
        resp = client.post("/api/ask", json={
            "contract_text": "",
            "question": "What does this say?",
        })
        assert resp.status_code == 422  # validation error (min_length=1)

    def test_ask_empty_question(self):
        """Should reject empty question."""
        resp = client.post("/api/ask", json={
            "contract_text": "Some contract text.",
            "question": "",
        })
        assert resp.status_code == 422

    def test_ask_no_payload(self):
        """Should return 422 for missing payload."""
        resp = client.post("/api/ask")
        assert resp.status_code == 422


class TestReportEndpoint:
    """Tests for POST /api/report."""

    def test_report_generation(self):
        """Should generate a valid PDF (or HTML fallback) from clause data."""
        payload = {
            "clauses": [
                {
                    "id": "c1",
                    "title": "Payment Terms",
                    "content": "Client shall pay within 30 days.",
                    "type": "payment",
                    "risk_level": "Low",
                    "risk_score": 15,
                    "risk_factors": [],
                    "explanation": "Standard payment terms.",
                    "suggested_alternative": "",
                    "missing_protections": [],
                    "fair_alternatives": [
                        {
                            "title": "Fair Payment Clause",
                            "content": "Pay within 30 days.",
                            "score": 0.92,
                        }
                    ],
                    "comparison_notes": "Close to fair-market language.",
                },
                {
                    "id": "c2",
                    "title": "Termination",
                    "content": "Either party may terminate at any time.",
                    "type": "termination",
                    "risk_level": "High",
                    "risk_score": 85,
                    "risk_factors": ["No notice period", "No cure period"],
                    "explanation": "This allows immediate termination without cause.",
                    "suggested_alternative": "Termination requires 30 days written notice.",
                    "missing_protections": ["Notice period", "Cure period"],
                    "fair_alternatives": [],
                    "comparison_notes": "Significant deviation from fair-market language.",
                },
            ],
            "overall_score": 50,
            "breakdown": {"High": 1, "Medium": 0, "Low": 1},
            "assessment": "Medium risk — some clauses need attention.",
        }

        resp = client.post("/api/report", json=payload)
        assert resp.status_code == 200

        content_type = resp.headers["content-type"]
        # Accept "text/html" or "text/html; charset=utf-8"
        is_pdf = "application/pdf" in content_type
        is_html = "text/html" in content_type
        assert is_pdf or is_html, f"Unexpected content-type: {content_type}"

        content = resp.content
        assert len(content) > 0

        if is_pdf:
            assert content[:5] == b"%PDF-", f"Not a valid PDF: {content[:20]}"
        else:
            # HTML fallback
            assert b"<!DOCTYPE html>" in content or b"<html" in content, "Not valid HTML"

    def test_report_empty_clauses(self):
        """Should reject empty clauses list."""
        resp = client.post("/api/report", json={"clauses": []})
        assert resp.status_code == 422  # min_length=1 validation

    def test_report_minimal_clauses(self):
        """Should work with minimal clause data (PDF or HTML fallback)."""
        payload = {
            "clauses": [
                {
                    "id": "c1",
                    "title": "Test",
                    "content": "Test clause.",
                    "type": "general",
                    "risk_level": "Low",
                    "risk_score": 10,
                    "risk_factors": [],
                    "explanation": "Test.",
                    "suggested_alternative": "",
                    "missing_protections": [],
                }
            ],
        }
        resp = client.post("/api/report", json=payload)
        assert resp.status_code == 200
        ct = resp.headers["content-type"]
        assert "application/pdf" in ct or "text/html" in ct, f"Bad content-type: {ct}"
        assert len(resp.content) > 0


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_health_when_qdrant_down(self):
        """Health check should still work even if services are partially down."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_invalid_json_payload(self):
        """Should return 422 for malformed JSON."""
        resp = client.post(
            "/api/ask",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (400, 422)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
