"""
ContractGuard - Structured JSON tracing.

One JSON object per line on the `contractguard.trace` logger (stdout via
the root handler). Each record carries the query/request, the retrieved
context, and the model + prompt versions behind the decision — enough to
replay or audit any answer.

Swap path: replace `trace_log` body with a LangSmith / Langfuse client
call. The call sites (llm_service, main) already pass `event`-shaped
payloads, so no other code changes are needed.
"""

import json
import logging
from typing import Any

logger = logging.getLogger("contractguard.trace")


def trace_log(event: str, **fields: Any) -> None:
    """Emit a single structured trace record."""
    record = {"event": event, **fields}
    logger.info(json.dumps(record, default=str))
