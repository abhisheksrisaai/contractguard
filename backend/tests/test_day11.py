"""
ContractGuard - Day 11 Tests
Verify multi-provider routing, quota fallthrough, sanitized fallbacks,
token trimming, and provider-chain ordering.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.llm_service import ContractAnalyzer, QUOTA_EXHAUSTED_MSG


@pytest.fixture(autouse=True)
def reset_daily_flags():
    """Reset provider cooldown/circuit state between tests."""
    from app.services.llm_service import analyzer
    analyzer.reset_state()


# ── 1. Provider order respected ───────────────────────────────────

def test_provider_order_uses_groq():
    """The default provider chain is Groq-only and serves requests."""
    from app.services.llm_service import analyzer

    assert "gemini" not in analyzer._ordered_providers("auto")
    with patch.object(analyzer, "_call_groq", return_value="ok") as mock_groq:
        result = analyzer._call_llm("system", "user", temperature=0.2, max_tokens=100)
        assert result == "ok"
        assert mock_groq.call_count >= 1


# ── 2. 429 daily-quota fallthrough (no sleep) ─────────────────────

def test_429_daily_quota_falls_through():
    """When provider 1 returns daily-quota 429, it falls to provider 2 without sleep."""
    from app.services.llm_service import analyzer
    from app.core.config import settings

    analyzer.reset_state()  # reset from prior tests
    call_order = []

    def routed_call(provider, *args, **kwargs):
        call_order.append(provider)
        if call_order.count(provider) == 1 and provider == call_order[0]:
            # First provider: simulate daily quota
            raise RuntimeError("429 TPD limit reached for model — upgrade to Dev Tier at https://console.groq.com/billing")
        return f"ok_from_{provider}"

    with patch.object(settings, "PROVIDER_ORDER", "groq,groq_8b"):
        with patch.object(analyzer, "_call_single_provider", routed_call):
            result = analyzer._call_llm("sys", "usr", 0.2, 100)
            assert "ok_from_" in result
            # First provider was tried
            assert len(call_order) >= 2, f"Expected at least 2 calls (fallthrough), got {call_order}"
            # Result came from second provider (not first)
            assert call_order[1] in result


# ── 3. All providers down → sanitized fallback ──────────────────

def test_all_providers_down_sanitized():
    """When all providers are exhausted, the clause is marked failed, not scored."""
    from app.services.llm_service import analyzer, ClauseAnalysisError

    # Make _call_llm always fail
    with patch.object(analyzer, "_call_llm", side_effect=RuntimeError("all dead")):
        clause = {"content": "The supplier shall deliver goods on time."}
        with pytest.raises(ClauseAnalysisError) as exc:
            analyzer.analyze_clause(clause)
        explanation = str(exc.value)
        # NO raw error text, no org IDs, no URLs
        for forbidden in ("429", "org_", "http", "RuntimeError", "all dead"):
            assert forbidden not in explanation, (
                f"Sanitized explanation leaked '{forbidden}': {explanation}"
            )
        assert "temporarily unavailable" in explanation.lower()
        assert QUOTA_EXHAUSTED_MSG == explanation


# ── 4. analyze_clause trims content to 1200 chars ────────────────

def test_clause_content_trimmed():
    """Content > 1200 chars is trimmed before the LLM call."""
    from app.services.llm_service import analyzer

    long_text = "x" * 3000
    clause = {"content": long_text, "title": "Test"}

    # Capture the content actually sent to the provider
    sent_content = []

    def capture_groq(system, user_message, temperature, max_tokens, model, **kwargs):
        sent_content.append(user_message)
        return '{"risk_level":"Low","risk_score":10,"risk_factors":[],"explanation":"ok","suggested_alternative":"","missing_protections":[]}'

    with patch.object(analyzer, "_call_groq", capture_groq):
        analyzer.analyze_clause(clause)

    # The prompt should contain the trimmed content (<=1200 + overhead)
    assert len(sent_content) > 0
    # content part should be at most ~1200 + prompt overhead (~300 chars)
    assert len(sent_content[0]) <= 2000  # generous upper bound


# ── 5. Unknown provider in PROVIDER_ORDER ignored ────────────────

def test_unknown_provider_ignored():
    """Unknown providers in PROVIDER_ORDER are skipped gracefully."""
    from app.services.llm_service import analyzer
    from app.core.config import settings

    # Patch PROVIDER_ORDER to include a bogus provider
    with patch.object(settings, "PROVIDER_ORDER", "bogus_provider,groq"):
        with patch.object(analyzer, "_call_groq", return_value="groq_ok"):
            # Reset provider state to ensure groq is tried
            analyzer.reset_state()
            result = analyzer._call_llm("sys", "usr", 0.2, 100)
            assert result == "groq_ok"


# ── 6. Daily quota marks provider exhausted for subsequent calls ─

def test_daily_quota_marks_exhausted():
    """After providers hit daily quota, they are skipped on later calls."""
    from app.services.llm_service import analyzer, ProviderError
    from app.core.config import settings

    analyzer.reset_state()
    call_order = []

    def mock_single(provider, *args, **kwargs):
        call_order.append(provider)
        raise RuntimeError("429 tokens per day (TPD) exceeded — upgrade")

    with patch.object(settings, "PROVIDER_ORDER", "groq,groq_8b"):
        with patch.object(analyzer, "_call_single_provider", mock_single):
            with pytest.raises(ProviderError):
                analyzer._call_llm("sys", "usr", 0.2, 100)
            assert "groq" in call_order
            assert "groq_8b" in call_order
            assert "groq" in analyzer._daily_exhausted
            assert "groq_8b" in analyzer._daily_exhausted

            call_order.clear()
            with pytest.raises(ProviderError):
                analyzer._call_llm("sys", "usr", 0.2, 100)
            assert call_order == []


# ── 7. Model override: "gemini" rejected ─────────────────────────

def test_analyze_model_gemini_rejected():
    """Gemini was removed from the model picker → 400."""
    import io, fitz
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 800)
    text = "EMPLOYMENT AGREEMENT\n\n1. Salary. Rs. 50,000 per month.\n\n2. Notice. 30 days.\n\n3. Law. India."
    page.insert_textbox(rect, text, fontsize=11, fontname="helv")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    files = {"file": ("test.pdf", io.BytesIO(buf.getvalue()), "application/pdf")}
    resp = client.post("/api/analyze", files=files, data={"model": "gemini"})
    if resp.status_code == 429:
        pytest.skip("Rate limited")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text[:200]}"
    assert "Unsupported model" in resp.json()["detail"]


def test_analyze_model_mixtral_rejected():
    """mixtral-8x7b-32768 is no longer in ALLOWED_MODELS → 400."""
    import io, fitz
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 800)
    page.insert_textbox(rect, "Test.", fontsize=11, fontname="helv")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    files = {"file": ("test.pdf", io.BytesIO(buf.getvalue()), "application/pdf")}
    resp = client.post("/api/analyze", files=files, data={"model": "mixtral-8x7b-32768"})
    if resp.status_code == 429:
        pytest.skip("Rate limited")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    assert "Unsupported model" in resp.json()["detail"]


def test_model_not_allowed_rejected():
    """Unknown model → 400."""
    import io, fitz
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 800)
    page.insert_textbox(rect, "Test.", fontsize=11, fontname="helv")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    files = {"file": ("test.pdf", io.BytesIO(buf.getvalue()), "application/pdf")}
    resp = client.post("/api/analyze", files=files, data={"model": "definitely-not-a-model"})
    if resp.status_code == 429:
        pytest.skip("Rate limited")
    assert resp.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
