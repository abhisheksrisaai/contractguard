"""
ContractGuard - Day 9 Tests
============================
Verify clause library expansion, threshold alignment, new analyze response
keys, model override validation, and contract_type_override.
"""

import io
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app

client = TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────────

def _make_test_pdf_bytes() -> bytes:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 800)
    page.insert_textbox(
        rect,
        "EMPLOYMENT AGREEMENT\n\n"
        "1. Appointment. The Employer appoints the Employee as Software Engineer.\n\n"
        "2. Salary. The Employee shall receive a monthly salary of Rs. 50,000.\n\n"
        "3. Notice Period. The Employee shall provide 30 days written notice.\n\n"
        "4. Confidentiality. The Employee shall maintain confidentiality.",
        fontsize=11, fontname="helv",
    )
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ── Fair Clauses Library ─────────────────────────────────────────────

class TestFairClausesLibrary:
    """Verify the expanded clause library."""

    @classmethod
    def setup_class(cls):
        path = (
            Path(__file__).resolve().parent.parent
            / "clause_library" / "fair_clauses.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            cls.clauses = json.load(f)

    def test_exactly_50_clauses(self):
        assert len(self.clauses) == 50, f"Expected 50 clauses, got {len(self.clauses)}"

    def test_all_required_fields(self):
        for i, c in enumerate(self.clauses):
            assert c.get("type"), f"Clause {i} missing type"
            assert c.get("title"), f"Clause {i} missing title"
            assert c.get("content"), f"Clause {i} missing content"
            assert len(c["content"]) >= 100, (
                f"Clause '{c['title']}' content too short ({len(c['content'])} chars)"
            )

    def test_unique_titles(self):
        titles = [c["title"] for c in self.clauses]
        dups = [t for t in titles if titles.count(t) > 1]
        assert not dups, f"Duplicate titles: {set(dups)}"

    def test_supplier_clauses_present(self):
        """At least 15 supplier_* clauses must exist."""
        supplier = [c for c in self.clauses if c["type"].startswith("supplier_")]
        assert len(supplier) >= 15, f"Expected >=15 supplier clauses, got {len(supplier)}"

    def test_works_clauses_present(self):
        """At least 15 works_* clauses must exist."""
        works = [c for c in self.clauses if c["type"].startswith("works_")]
        assert len(works) >= 15, f"Expected >=15 works clauses, got {len(works)}"


# ── Report Thresholds ────────────────────────────────────────────────

class TestReportThresholds:
    """Verify report generator uses >=75 / >=45 thresholds."""

    def test_score_72_is_medium(self):
        from app.services.report_generator import ReportGenerator
        rg = ReportGenerator()
        # Build a simple analysis with score 72
        analysis = {
            "clauses": [{
                "id": "c1", "title": "T", "content": "T", "type": "general",
                "risk_level": "High", "risk_score": 72,
                "risk_factors": [], "explanation": "", "suggested_alternative": "",
                "missing_protections": [],
            }],
            "overall_score": 72,
            "breakdown": {"High": 1, "Medium": 0, "Low": 0},
            "assessment": "Test",
            "total_clauses": 1,
        }
        result = rg.generate_report(analysis)
        html = result.decode("utf-8") if isinstance(result, bytes) else result
        # Score 72 should be "Medium Risk", not "High Risk"
        assert "Medium Risk" in html, f"Expected Medium Risk in report. HTML snippet: {html[:500]}"


# ── /api/analyze new keys ───────────────────────────────────────────

class TestAnalyzeNewKeys:
    """Verify the /api/analyze response contains new fields."""

    def test_analyze_response_has_new_keys(self):
        pdf_bytes = _make_test_pdf_bytes()
        files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        resp = client.post("/api/analyze", files=files)

        if resp.status_code == 429:
            pytest.skip("Rate limited")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data = resp.json()

        # Old keys must still exist
        for key in ("success", "overall_score", "risk_breakdown", "clauses", "assessment"):
            assert key in data, f"Missing legacy key: {key}"

        # New keys
        new_keys = [
            "contract_type", "type_confidence", "red_flags",
            "missing_clauses", "negotiation_opportunities",
            "recommended_action", "confidence", "executive_summary",
            "analysis_time_seconds",
        ]
        for key in new_keys:
            assert key in data, f"Missing new key: {key}"

        assert isinstance(data["red_flags"], list)
        assert isinstance(data["analysis_time_seconds"], (int, float))
        assert data["analysis_time_seconds"] > 0


# ── Model override ───────────────────────────────────────────────────

class TestModelOverride:
    """Verify model validation in /api/analyze and /api/ask."""

    def test_analyze_rejects_bad_model(self):
        pdf_bytes = _make_test_pdf_bytes()
        files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {"model": "gpt-4-turbo"}
        resp = client.post("/api/analyze", files=files, data=data)
        # 429 if rate-limited from prior tests, 400 for bad model
        assert resp.status_code in (400, 429), (
            f"Expected 400 or 429, got {resp.status_code}: {resp.text[:200]}"
        )
        if resp.status_code == 400:
            assert "Unsupported model" in resp.json()["detail"]

    def test_ask_rejects_bad_model(self):
        resp = client.post("/api/ask", json={
            "contract_text": "A valid contract.",
            "question": "What does it say?",
            "model": "o1-preview",
        })
        if resp.status_code == 429:
            pytest.skip("Rate limited")
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text[:200]}"
        assert "Unsupported model" in resp.json()["detail"]

    def test_ask_accepts_allowlisted_model(self):
        resp = client.post("/api/ask", json={
            "contract_text": "A valid contract text about payment.",
            "question": "What payment terms?",
            "model": "mixtral-8x7b-32768",
        })
        if resp.status_code == 429:
            pytest.skip("Rate limited")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert data["success"] is True
        assert "model" in data


# ── contract_type_override ───────────────────────────────────────────

class TestContractTypeOverride:
    """Verify contract_type_override form field."""

    def test_analyze_with_contract_type_override(self):
        pdf_bytes = _make_test_pdf_bytes()
        files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {"contract_type_override": "employment_contract"}
        resp = client.post("/api/analyze", files=files, data=data)

        if resp.status_code == 429:
            pytest.skip("Rate limited")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
        data_resp = resp.json()
        assert data_resp["contract_type"] == "employment_contract"
        assert data_resp["type_confidence"] == 1.0

    def test_analyze_rejects_invalid_override(self):
        pdf_bytes = _make_test_pdf_bytes()
        files = {"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {"contract_type_override": "bogus_type"}
        resp = client.post("/api/analyze", files=files, data=data)
        if resp.status_code == 429:
            pytest.skip("Rate limited")
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text[:200]}"
        assert "Invalid contract_type" in resp.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
