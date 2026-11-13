"""Contract tests for the shared state vocabulary.

The frontend and API consumers depend on the literal string values. These tests
fail if an enum is renamed or if a helper starts emitting a different case.
"""

import json
import logging

from app.core.status import (
    ANALYSIS_STATUS_VALUES,
    CLAUSE_STATUS_VALUES,
    FIVE_C_STATUS_VALUES,
    PIPELINE_STAGES,
    AnalysisStatus,
    ClauseStatus,
    FiveCStatus,
    ParseQuality,
    PipelineStage,
)


def test_analysis_status_wire_values_are_stable():
    assert ANALYSIS_STATUS_VALUES == ("complete", "partial")
    assert AnalysisStatus.COMPLETE.value == "complete"
    assert AnalysisStatus.PARTIAL.value == "partial"


def test_clause_and_five_c_wire_values_are_stable():
    assert CLAUSE_STATUS_VALUES == ("complete", "failed")
    assert FIVE_C_STATUS_VALUES == ("complete", "partial", "unavailable")
    assert ParseQuality.DIRECT.value == "direct"
    assert ParseQuality.RECOVERED.value == "recovered"
    assert ParseQuality.FAILED.value == "failed"


def test_pipeline_stages_are_ordered_and_unique():
    assert PIPELINE_STAGES == (
        "validate", "extract", "classify", "red_flags", "segment",
        "skills", "clauses", "aggregate",
    )
    assert len(set(PIPELINE_STAGES)) == len(PIPELINE_STAGES)
    assert PipelineStage.AGGREGATE.value == PIPELINE_STAGES[-1]


def test_trace_stage_emits_one_structured_record(caplog):
    from main import _trace_stage

    with caplog.at_level(logging.INFO, logger="contractguard.trace"):
        _trace_stage("req-1", PipelineStage.EXTRACT, characters=123)

    payload = json.loads(caplog.records[-1].message)
    assert payload == {
        "event": "pipeline_stage",
        "request_id": "req-1",
        "stage": "extract",
        "status": "complete",
        "characters": 123,
    }


def test_five_c_state_reports_complete_partial_and_unavailable():
    from app.skills.skill_analyzer import SkillAnalyzer

    complete = {
        key: {"status": "Pass", "score": 90}
        for key in ("capacity", "consent", "consideration", "clarity", "compliance")
    }
    assert SkillAnalyzer._five_c_state(complete) == FiveCStatus.COMPLETE.value

    partial = dict(complete)
    partial["clarity"] = {"status": "Unavailable", "score": None}
    assert SkillAnalyzer._five_c_state(partial) == FiveCStatus.PARTIAL.value

    unavailable = {
        key: {"status": "Unavailable", "score": None}
        for key in complete
    }
    assert SkillAnalyzer._five_c_state(unavailable) == FiveCStatus.UNAVAILABLE.value


def test_failed_clause_result_uses_the_shared_clause_status():
    from main import _failed_clause_result

    result = _failed_clause_result(
        {"id": "c1", "title": "Notice", "content": "30 days."}, 0,
    )
    assert result["analysis_status"] == ClauseStatus.FAILED.value
    assert result["risk_score"] is None
    assert result["needs_human_review"] is True


def test_report_defaults_to_the_complete_analysis_status():
    from app.services.report_generator import _safe_context

    context = _safe_context({"clauses": []})
    assert context["analysis_status"] == AnalysisStatus.COMPLETE.value
