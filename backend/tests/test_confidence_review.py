"""
ContractGuard - Confidence threshold + human review + tracing tests.

Fully offline (LLM calls are mocked). Verifies:
- clean model JSON -> high confidence, auto-scored (no review flag)
- unparsable output -> heuristic confidence, flagged for human review
- provider outage -> Medium/50 fallback, confidence 40, flagged
- short clauses take the thin-signal penalty
- trace_log emits one JSON record per call with the required keys
"""

import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.llm_service import (
    CONFIDENCE_REVIEW_THRESHOLD,
    ContractAnalyzer,
)

LONG_CLAUSE = {
    "id": "c1",
    "title": "Termination",
    "type": "termination",
    "content": (
        "The Employer may terminate employment at any time without notice or cause. "
        "The Employee forfeits all unpaid benefits upon termination, including accrued "
        "leave encashment and pending bonuses, regardless of tenure or performance."
    ),
}

VALID_JSON = json.dumps({
    "risk_level": "High",
    "risk_score": 90,
    "risk_factors": ["No notice required", "Benefits forfeited"],
    "explanation": "One-sided termination with no protections.",
    "suggested_alternative": "Either party may terminate with 30 days notice.",
    "missing_protections": ["Notice period", "Severance"],
})


def _analyzer():
    return ContractAnalyzer()


def test_threshold_constant():
    assert CONFIDENCE_REVIEW_THRESHOLD == 60


def test_clean_json_is_auto_scored():
    analyzer = _analyzer()
    with patch.object(analyzer, "_call_llm", return_value=VALID_JSON):
        result = analyzer.analyze_clause(dict(LONG_CLAUSE))
    assert result["risk_level"] == "High"
    assert result["confidence"] == 85
    assert result["needs_human_review"] is False


def test_heuristic_parse_is_flagged():
    analyzer = _analyzer()
    garbage = "risk is high trust me " * 20  # no JSON object at all
    with patch.object(analyzer, "_call_llm", return_value=garbage):
        result = analyzer.analyze_clause(dict(LONG_CLAUSE))
    assert result["confidence"] == 55
    assert result["needs_human_review"] is True


def test_provider_outage_falls_back_and_flags():
    analyzer = _analyzer()
    with patch.object(analyzer, "_call_llm", side_effect=RuntimeError("all down")):
        result = analyzer.analyze_clause(dict(LONG_CLAUSE))
    assert result["risk_level"] == "Medium"
    assert result["risk_score"] == 50
    assert result["confidence"] == 40
    assert result["needs_human_review"] is True


def test_short_clause_takes_thin_signal_penalty():
    analyzer = _analyzer()
    short = {"id": "c2", "title": "Note", "type": "general",
             "content": "Pay within 30 days of invoice."}
    with patch.object(analyzer, "_call_llm", return_value=VALID_JSON):
        result = analyzer.analyze_clause(short)
    assert result["confidence"] == 75  # 85 - 10 thin signal
    assert result["needs_human_review"] is False


def test_empty_clause_is_confident_low():
    result = _analyzer().analyze_clause({"id": "c3", "content": "   "})
    assert result["risk_level"] == "Low"
    assert result["needs_human_review"] is False


def test_trace_log_emits_json_record(caplog):
    from app.core.tracing import trace_log

    with caplog.at_level(logging.INFO, logger="contractguard.trace"):
        trace_log("clause_scored", request_id="abc", clause_id="c1",
                  confidence=85, needs_human_review=False)
    records = [
        json.loads(r.message) for r in caplog.records
        if r.name == "contractguard.trace"
    ]
    assert records, "no trace record emitted"
    rec = records[-1]
    assert rec["event"] == "clause_scored"
    assert rec["clause_id"] == "c1"
    assert rec["confidence"] == 85
