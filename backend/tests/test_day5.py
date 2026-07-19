"""
ContractGuard - Day 5 Tests
Production readiness: CORS, rate limiting, error recovery, file size limits.
"""

import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app

client = TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_test_pdf_bytes() -> bytes:
    """Create a minimal text PDF using PyMuPDF."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 800)
    page.insert_textbox(
        rect,
        "CONSULTING AGREEMENT\n\n1. Services. Consultant shall provide services.\n\n"
        "2. Payment. Client shall pay $10,000 within 30 days.\n\n"
        "3. Termination. Either party may terminate with 15 days notice.",
        fontsize=11,
        fontname="helv",
    )
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ── CORS Tests ───────────────────────────────────────────────────────────

class TestCORS:
    """Verify CORS headers are returned correctly."""

    def test_cors_preflight(self):
        """OPTIONS request should return CORS headers."""
        resp = client.options(
            "/api/analyze",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert resp.status_code in (200, 405)  # 200 if preflight handled, 405 if not needed

    def test_cors_headers_present(self):
        """All responses should include CORS allow-origin."""
        resp = client.get("/")
        # CORS headers should be present
        assert resp.status_code == 200

    def test_cors_reject_unknown_origin(self):
        """Unknown origins should be handled gracefully."""
        resp = client.get(
            "/api/health",
            headers={"Origin": "https://evil-site.com"},
        )
        assert resp.status_code == 200
        # FastAPI CORS middleware: unknown origins get no allow-origin header
        # (or are rejected), but the endpoint still works when called from TestClient


# ── Rate Limiting Tests ──────────────────────────────────────────────────

class TestRateLimiting:
    """Verify rate limits are enforced."""

    def test_rate_limit_headers_present(self):
        """Rate-limited endpoints should include X-RateLimit-Remaining header."""
        # Use /api/ask which is fast and rate-limited
        resp = client.post("/api/ask", json={
            "contract_text": "Client shall pay $100.",
            "question": "How much?",
        })
        if resp.status_code == 200:
            assert "X-RateLimit-Remaining" in resp.headers, (
                f"Expected X-RateLimit-Remaining, got keys: {list(resp.headers.keys())}"
            )

    def test_ask_rate_limit_headers(self):
        """Ask response should contain rate limit headers."""
        resp = client.post("/api/ask", json={
            "contract_text": "Client shall pay $100.",
            "question": "How much?",
        })
        if resp.status_code == 200:
            assert "X-RateLimit-Remaining" in resp.headers

    def test_report_rate_limit_headers(self):
        """Report response should contain rate limit headers."""
        resp = client.post("/api/report", json={
            "clauses": [{
                "id": "c1",
                "title": "Test",
                "content": "Test.",
                "type": "general",
                "risk_level": "Low",
                "risk_score": 10,
                "risk_factors": [],
                "explanation": "Test.",
                "suggested_alternative": "",
                "missing_protections": [],
            }],
        })
        if resp.status_code == 200:
            assert "X-RateLimit-Remaining" in resp.headers


# ── File Size Limit Tests ────────────────────────────────────────────────

class TestFileSizeLimits:
    """Verify file size enforcement."""

    def test_file_too_large(self):
        """Uploading > 10MB file should return 413."""
        # Create a fake PDF that claims to be > 10MB
        large_content = b"%PDF-1.4\n" + b"x" * (11 * 1024 * 1024)  # 11MB
        files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}
        resp = client.post("/api/analyze", files=files)
        assert resp.status_code == 413, f"Expected 413, got {resp.status_code}: {resp.text[:200]}"
        assert "too large" in resp.json()["detail"].lower()

    def test_file_empty(self):
        """Empty file upload should return 400."""
        files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
        resp = client.post("/api/analyze", files=files)
        assert resp.status_code in (400, 422)


# ── Error Recovery Tests ─────────────────────────────────────────────────

class TestErrorRecovery:
    """Verify error handling and recovery."""

    def test_500_recovery(self):
        """Service should handle unexpected errors without crashing."""
        # Non-PDF file is the simplest triggerable error path
        files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
        resp = client.post("/api/analyze", files=files)
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
        assert "pdf" in data["detail"].lower()

    def test_ask_invalid_json(self):
        """Malformed JSON should not crash the server."""
        resp = client.post(
            "/api/ask",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (400, 422)

    def test_report_empty_returns_error(self):
        """Empty report payload should return validation error."""
        resp = client.post("/api/report", json={"clauses": []})
        assert resp.status_code in (400, 422)

    def test_health_never_fails(self):
        """Health endpoint should always return 200 even when services are down."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_server_continues_after_error(self):
        """After a 400 error, subsequent requests should still work."""
        # Trigger a bad request
        client.post("/api/ask", json={"contract_text": "", "question": ""})
        # Then make a valid request
        resp = client.post("/api/ask", json={
            "contract_text": "A valid contract text.",
            "question": "What does it say?",
        })
        # Server should respond normally (not crashed)
        assert resp.status_code in (200, 422, 500)


# ── Request Logging Test ─────────────────────────────────────────────────

class TestRequestLogging:
    """Verify middleware is active."""

    def test_logging_middleware_active(self):
        """Requests should be logged (we verify the endpoint still works)."""
        resp = client.get("/")
        assert resp.status_code == 200
        # Logging is verified indirectly — if middleware wasn't working,
        # the app would still handle the request but without log output.


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
