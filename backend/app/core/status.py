"""Wire-contract state values shared by the analysis pipeline.

These enums are intentionally small and additive: the JSON values are exactly
the strings the API already returned, so clients and stored reports keep
working. Centralising them prevents one module from emitting "unavailable"
while another emits "failed" for the same condition.

The frontend mirrors the consumer-facing values in
``frontend/src/state/analysisMachine.js``. Keep the two lists in sync.
"""

from enum import Enum


class AnalysisStatus(str, Enum):
    """Terminal state of a POST /api/analyze request that returned 200."""

    COMPLETE = "complete"
    PARTIAL = "partial"


class ClauseStatus(str, Enum):
    """Terminal state of one clause inside an analysis."""

    COMPLETE = "complete"
    FAILED = "failed"


class FiveCStatus(str, Enum):
    """Completeness of the 5C enforceability block."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class ParseQuality(str, Enum):
    """How cleanly a model response parsed."""

    DIRECT = "direct"
    RECOVERED = "recovered"
    HEURISTIC = "heuristic"
    FAILED = "failed"
    EMPTY = "empty"


class PipelineStage(str, Enum):
    """Backend pipeline stages, in execution order.

    The pipeline is synchronous today, so these are observable in logs rather
    than returned as per-stage progress. They exist as a stable vocabulary for
    tracing and for a future job/status endpoint.
    """

    VALIDATE = "validate"
    EXTRACT = "extract"
    CLASSIFY = "classify"
    RED_FLAGS = "red_flags"
    SEGMENT = "segment"
    SKILLS = "skills"
    CLAUSES = "clauses"
    AGGREGATE = "aggregate"


PIPELINE_STAGES = tuple(stage.value for stage in PipelineStage)

ANALYSIS_STATUS_VALUES = tuple(status.value for status in AnalysisStatus)
CLAUSE_STATUS_VALUES = tuple(status.value for status in ClauseStatus)
FIVE_C_STATUS_VALUES = tuple(status.value for status in FiveCStatus)
