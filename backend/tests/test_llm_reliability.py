"""Provider routing, quota classification, and failure-handling tests.

These tests are offline: provider calls are mocked, so they do not consume
Groq quota or depend on network access.
"""

import json
import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.core.status import PIPELINE_STAGES
from app.services.llm_service import (
    ContractAnalyzer,
    ProviderError,
    QUOTA_EXHAUSTED_MSG,
    _ProviderState,
    _classify_error,
    analyzer,
)


@pytest.fixture(autouse=True)
def clean_state():
    analyzer.reset_state()
    yield
    analyzer.reset_state()


def test_default_selector_is_qwen():
    from main import _validate_model
    assert _validate_model(None) == "qwen/qwen3.8-27b"
    assert _validate_model("auto") == "qwen/qwen3.8-27b"


def test_invalid_selector_is_not_passed_to_groq():
    a = ContractAnalyzer()
    with patch.object(a, "_call_groq", return_value="ok") as mock:
        a._call_single_provider("groq", "sys", "user", 0.2, 100, "gemini")
    assert mock.call_args.args[4] == settings.GROQ_MODEL
    assert mock.call_args.args[4] != "gemini"


def test_provider_failure_falls_back_to_next():
    a = ContractAnalyzer()
    calls = []

    def mock_single(provider, *args, **kwargs):
        calls.append(provider)
        if provider == "groq":
            raise ProviderError(
                "rate limited", kind="rate_limit", provider="groq", retry_after=0,
            )
        return f"ok_{provider}"

    with patch.object(settings, "PROVIDER_ORDER", "groq,groq_8b"):
        with patch.object(a, "_call_single_provider", mock_single):
            assert a._call_llm("sys", "user") == "ok_groq_8b"
    assert calls[0] == "groq"
    assert "groq_8b" in calls


def test_slow_primary_still_leaves_time_for_fallback():
    a = ContractAnalyzer()
    calls = []
    clock = {"now": 1000.0}

    def mock_single(provider, *args, **kwargs):
        calls.append(provider)
        if provider == "groq":
            clock["now"] += 30.0  # a slow provider timeout
            raise ProviderError("timeout", kind="timeout", provider="groq")
        return "ok"

    with patch.object(settings, "PROVIDER_ORDER", "groq,groq_8b"):
        with patch("app.services.llm_service.time.monotonic", side_effect=lambda: clock["now"]):
            with patch.object(a, "_call_single_provider", mock_single):
                result = a._call_llm("sys", "user")

    assert result == "ok"
    assert calls == ["groq", "groq_8b"]


def test_unusable_response_falls_through_to_next_provider():
    a = ContractAnalyzer()
    calls = []

    def mock_single(provider, *args, **kwargs):
        calls.append(provider)
        if provider == "groq":
            return "I think this clause is risky, but here is no JSON."
        return '{"risk_level":"Low","risk_score":10}'

    with patch.object(settings, "PROVIDER_ORDER", "groq,groq_120b"):
        with patch.object(a, "_call_single_provider", mock_single):
            result = a._call_llm(
                "sys", "user",
                validator=lambda raw: raw.strip().startswith("{"),
            )

    assert result.startswith("{")
    assert calls[:2] == ["groq", "groq_120b"]


def test_missing_decision_fields_falls_through():
    a = ContractAnalyzer()
    calls = []

    def mock_single(provider, *args, **kwargs):
        calls.append(provider)
        if provider == "groq":
            return '{"explanation":"this looks risky"}'
        return '{"risk_level":"High","risk_score":80,"explanation":"uncapped liability"}'

    with patch.object(settings, "PROVIDER_ORDER", "groq,groq_120b"):
        with patch.object(a, "_call_single_provider", mock_single):
            result = a.analyze_clause(
                {"id": "c1", "title": "Liability", "type": "liability", "content": "x" * 200},
                model="qwen/qwen3.8-27b",
            )

    assert result["risk_level"] == "High"
    assert result["risk_score"] == 80
    assert calls[:2] == ["groq", "groq_120b"]


def test_rpm_rate_limit_is_not_daily_quota():
    error = RuntimeError(
        "429 Rate limit reached for model `openai/gpt-oss-120b` on tokens per "
        "minute (TPM): Limit 8000, Used 9000."
    )
    assert _classify_error(error, "groq").kind == "rate_limit"


def test_tpm_429_with_billing_link_is_not_daily_quota():
    error = RuntimeError(
        "429 Rate limit reached for model `qwen/qwen3.8-27b` on tokens per "
        "minute (TPM): Limit 8000, Used 9000. Upgrade at "
        "https://console.groq.com/settings/billing. Resets per day at midnight."
    )
    assert _classify_error(error, "groq").kind == "rate_limit"


def test_daily_quota_is_classified_as_daily():
    error = RuntimeError(
        "429 TPD limit reached for model — upgrade to Dev Tier at "
        "https://console.groq.com/billing"
    )
    assert _classify_error(error, "groq").kind == "daily_quota"


def test_tpd_429_with_model_phrase_is_still_daily_quota():
    error = RuntimeError(
        "Rate limit reached for model `openai/gpt-oss-120b` in organization "
        "`org_x` service tier `on_demand` on tokens per day (TPD): Limit "
        "200000, Used 200100."
    )
    assert _classify_error(error, "groq").kind == "daily_quota"


def test_output_tpm_429_is_not_daily_quota():
    error = RuntimeError(
        "Request too large for model `qwen/qwen3.8-27b` on output tokens per "
        "minute (OTPM): Limit 1000, Requested 1600."
    )
    assert _classify_error(error, "groq").kind == "rate_limit"


def test_ordered_providers_use_qwen_only():
    a = ContractAnalyzer()
    assert a._ordered_providers("auto") == ["groq"]
    assert a._ordered_providers("openai/gpt-oss-120b") == ["groq"]
    assert a._ordered_providers("qwen/qwen3.8-27b") == ["groq"]


def test_unavailable_five_c_is_not_fabricated():
    from app.skills.skill_analyzer import SkillAnalyzer

    five_c = SkillAnalyzer._unavailable_five_c()
    assert set(five_c) == {"capacity", "consent", "consideration", "clarity", "compliance"}
    assert all(data["status"] == "Unavailable" for data in five_c.values())
    assert all(data["score"] is None for data in five_c.values())


def test_partial_five_c_keeps_scored_rows_and_marks_the_rest_unavailable():
    from app.skills.skill_analyzer import SkillAnalyzer

    payload = {
        "Capacity": {"status": "Pass", "score": 90, "issues": []},
        "consent": {"status": "Fail", "score": 10, "issues": ["No consent."]},
    }
    partial = SkillAnalyzer._normalize_five_c(payload, require_all=False)
    assert partial["capacity"]["score"] == 90
    assert partial["consent"]["score"] == 10
    assert partial["consideration"]["score"] is None
    assert partial["clarity"]["status"] == "Unavailable"
    assert SkillAnalyzer._five_c_state(partial) == "partial"

    with pytest.raises(ValueError):
        SkillAnalyzer._normalize_five_c(payload, require_all=True)


def test_invalid_model_is_not_retried():
    a = ContractAnalyzer()
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError(
        "Error code: 404 - model_not_found"
    )
    a._groq_client = client

    with pytest.raises(ProviderError) as exc:
        a._call_groq("sys", "user", 0.2, 100, "openai/gpt-oss-120b")

    assert exc.value.kind == "invalid_model"
    assert client.chat.completions.create.call_count == 1


def test_rate_limit_retries_then_raises():
    a = ContractAnalyzer()
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError(
        "429 Rate limit reached for model on tokens per minute (TPM)."
    )
    a._groq_client = client

    with patch("app.services.llm_service.time.sleep") as sleep:
        with pytest.raises(ProviderError) as exc:
            a._call_groq("sys", "user", 0.2, 100, "openai/gpt-oss-120b")

    assert client.chat.completions.create.call_count == settings.LLM_MAX_RETRIES + 1
    assert exc.value.kind == "rate_limit"
    assert sleep.call_count == settings.LLM_MAX_RETRIES


def test_daily_quota_cooldown_expires():
    a = ContractAnalyzer()
    a._mark_daily_exhausted("groq")
    assert "groq" in a._daily_exhausted
    assert not a._is_provider_available("groq")

    with patch(
        "app.services.llm_service.time.time",
        return_value=time.time() + 2 * 86400,
    ):
        a._clear_daily_exhausted_if_needed()
        assert a._is_provider_available("groq")


def test_circuit_half_open_allows_one_probe():
    a = ContractAnalyzer()
    a._provider_states["groq"] = _ProviderState(
        consecutive_failures=settings.LLM_CIRCUIT_FAILURE_THRESHOLD,
        open_until=time.monotonic() - 1,
    )
    assert a._is_provider_available("groq") is True
    assert a._is_provider_available("groq") is False
    a._record_success("groq")
    assert a._is_provider_available("groq") is True


def test_failed_clause_has_no_fabricated_score():
    from main import _failed_clause_result
    result = _failed_clause_result(
        {"id": "c1", "title": "Termination", "content": "text"}, 0,
    )
    assert result["analysis_status"] == "failed"
    assert result["risk_level"] == "Unknown"
    assert result["risk_score"] is None
    assert result["needs_human_review"] is True
    assert QUOTA_EXHAUSTED_MSG  # import stays meaningful for the failure path


def test_overall_score_ignores_unscored_clauses():
    a = ContractAnalyzer()
    result = a.analyze_contract([
        {"risk_level": "High", "risk_score": 90},
        {"risk_level": "Unknown", "risk_score": None},
    ])
    assert result["overall_score"] == 90
    assert result["risk_breakdown"] == {"High": 1, "Medium": 0, "Low": 0}


def _pdf_file():
    return {"file": ("test.pdf", b"%PDF-1.4\n", "application/pdf")}


def _clause(clause_id: str) -> dict:
    return {
        "id": clause_id,
        "title": f"Clause {clause_id}",
        "content": f"Content for {clause_id}",
        "type": "general",
    }


def _scored_clause(clause: dict) -> dict:
    return {
        **clause,
        "risk_level": "High",
        "risk_score": 90,
        "risk_factors": [],
        "explanation": "Test clause.",
        "suggested_alternative": "",
        "missing_protections": [],
        "fair_alternatives": [],
        "comparison_notes": "",
        "confidence": 85,
        "needs_human_review": False,
        "analysis_status": "complete",
    }


def test_models_endpoint_lists_only_qwen():
    from fastapi.testclient import TestClient
    from main import app

    response = TestClient(app).get("/api/models")
    assert response.status_code == 200
    body = response.json()
    assert body["default"] == "qwen/qwen3.8-27b"
    ids = {item["id"] for item in body["models"]}
    assert ids == {"qwen/qwen3.8-27b"}
    assert "gemini" not in ids


def test_analyze_returns_503_when_every_clause_fails():
    from fastapi.testclient import TestClient
    import main

    client = TestClient(main.app)
    with patch.object(main.pdf_extractor, "extract_text", return_value="contract text"), \
         patch.object(main.pdf_extractor, "segment_clauses", return_value=[_clause("c1")]), \
         patch.object(main, "_analyze_single_clause", side_effect=RuntimeError("provider down")):
        response = client.post("/api/analyze", files=_pdf_file())

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"].lower()
    assert response.headers.get("retry-after") == "60"


def test_analyze_marks_partial_results_and_keeps_score_honest(caplog):
    from fastapi.testclient import TestClient
    import main

    caplog.set_level(logging.INFO, logger="contractguard.trace")
    clauses = [_clause("c1"), _clause("c2")]

    def fake_analyze(clause, model, request_id):
        if clause["id"] == "c1":
            return _scored_clause(clause)
        raise RuntimeError("provider down")

    client = TestClient(main.app)
    with patch.object(main.pdf_extractor, "extract_text", return_value="contract text"), \
         patch.object(main.pdf_extractor, "segment_clauses", return_value=clauses), \
         patch.object(main, "_analyze_single_clause", side_effect=fake_analyze), \
         patch.object(main.skill_analyzer, "analyze", return_value={
             "five_c": None, "findings": [], "missing_clauses": [],
             "negotiation_opportunities": [], "recommended_action": None,
             "confidence": 0, "executive_summary": "",
         }):
        response = client.post("/api/analyze", files=_pdf_file())

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_status"] == "partial"
    assert data["analyzed_clause_count"] == 1
    assert data["failed_clause_count"] == 1
    assert data["overall_score"] == 90
    failed = [c for c in data["clauses"] if c["analysis_status"] == "failed"]

    stage_events = [
        json.loads(record.message)
        for record in caplog.records
        if record.name == "contractguard.trace"
        and json.loads(record.message).get("event") == "pipeline_stage"
    ]
    assert [event["stage"] for event in stage_events] == list(PIPELINE_STAGES)
    assert all(event["request_id"] for event in stage_events)
    assert len(failed) == 1
    assert failed[0]["risk_score"] is None
    assert failed[0]["risk_level"] == "Unknown"
