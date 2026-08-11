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
    """Reset daily exhaustion flags between tests."""
    from app.services.llm_service import analyzer
    analyzer._daily_exhausted = set()


# ── 1. Provider order respected ───────────────────────────────────

def test_provider_order_no_gemini_key():
    """With GEMINI_API_KEY empty, gemini is skipped and groq used."""
    from app.services.llm_service import analyzer
    from app.core.config import settings

    # Ensure gemini is not available
    with patch.object(settings, "GEMINI_API_KEY", ""):
        # The client re-init check uses settings.has_gemini → False
        assert not settings.has_gemini

    # _call_llm with gemini,groq,groq_8b should skip gemini, use groq
    with patch.object(analyzer, "_call_groq", return_value="ok") as mock_groq:
        result = analyzer._call_llm("system", "user", temperature=0.2, max_tokens=100)
        assert result == "ok"
        # gemini should have been skipped without API key, groq was used
        assert mock_groq.call_count >= 1


# ── 2. 429 daily-quota fallthrough (no sleep) ─────────────────────

def test_429_daily_quota_falls_through():
    """When provider 1 returns daily-quota 429, it falls to provider 2 without sleep."""
    from app.services.llm_service import analyzer
    from app.core.config import settings

    analyzer._daily_exhausted = set()  # reset from prior tests
    call_order = []

    def routed_call(provider, *args, **kwargs):
        call_order.append(provider)
        if call_order.count(provider) == 1 and provider == call_order[0]:
            # First provider: simulate daily quota
            raise RuntimeError("429 TPD limit reached for model — upgrade to Dev Tier at https://console.groq.com/billing")
        return f"ok_from_{provider}"

    with patch.object(analyzer, "_call_single_provider", routed_call):
        result = analyzer._call_llm("sys", "usr", 0.2, 100)
        assert "ok_from_" in result
        # First provider was tried
        assert len(call_order) >= 2, f"Expected at least 2 calls (fallthrough), got {call_order}"
        # Result came from second provider (not first)
        assert call_order[1] in result


# ── 3. All providers down → sanitized fallback ──────────────────

def test_all_providers_down_sanitized():
    """When all providers are exhausted, analyze_clause returns clean fallback (no leaks)."""
    from app.services.llm_service import analyzer

    # Make _call_llm always fail
    with patch.object(analyzer, "_call_llm", side_effect=RuntimeError("all dead")):
        clause = {"content": "The supplier shall deliver goods on time."}
        result = analyzer.analyze_clause(clause)
        assert result["risk_level"] == "Medium"
        assert result["risk_score"] == 50
        explanation = result["explanation"]
        # NO raw error text, no org IDs, no URLs
        for forbidden in ("429", "org_", "http", "RuntimeError", "all dead"):
            assert forbidden not in explanation, (
                f"Sanitized explanation leaked '{forbidden}': {explanation}"
            )
        assert "temporarily unavailable" in explanation.lower()
        assert QUOTA_EXHAUSTED_MSG in explanation


# ── 4. analyze_clause trims content to 1200 chars ────────────────

def test_clause_content_trimmed():
    """Content > 1200 chars is trimmed before the LLM call."""
    from app.services.llm_service import analyzer

    long_text = "x" * 3000
    clause = {"content": long_text, "title": "Test"}

    # Capture the content actually sent to the provider
    sent_content = []

    def capture_groq(system, user_message, temperature, max_tokens, model):
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
            # Reset daily_exhausted to ensure groq is tried
            analyzer._daily_exhausted = set()
            result = analyzer._call_llm("sys", "usr", 0.2, 100)
            assert result == "groq_ok"


# ── 6. Daily quota marks provider exhausted for subsequent calls ─

def test_daily_quota_marks_exhausted():
    """After a provider hits daily quota, it's skipped on subsequent calls."""
    from app.services.llm_service import analyzer, ContractAnalyzer

    analyzer._daily_exhausted = set()
    call_order = []

    def mock_single(provider, *args, **kwargs):
        call_order.append(provider)
        if provider == "gemini":
            raise RuntimeError("429 tokens per day (TPD) exceeded — upgrade")
        if provider == "groq":
            return "groq_ok"

    with patch.object(analyzer, "_call_single_provider", mock_single):
        # First call: gemini fails, groq succeeds
        result1 = analyzer._call_llm("sys", "usr", 0.2, 100)
        assert result1 == "groq_ok"
        assert "gemini" in call_order
        assert "groq" in call_order
        # gemini should now be in _daily_exhausted
        assert "gemini" in analyzer._daily_exhausted

        call_order.clear()
        # Second call: gemini should be skipped, groq used directly
        result2 = analyzer._call_llm("sys", "usr", 0.2, 100)
        assert result2 == "groq_ok"
        # gemini should NOT be in this call_order
        assert "gemini" not in call_order
        assert call_order[0] == "groq"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
