"""
ContractGuard - LLM Risk Analysis Service
Multi-provider routing with retries, cooldowns, and explicit failure.
"""

import json
import logging
import random
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from app.core.config import settings
from app.core.status import ClauseStatus, ParseQuality
from app.core.tracing import trace_log

logger = logging.getLogger(__name__)

# ── Prompt versions (bump when the template text changes) ────────────
SYSTEM_PROMPT_VERSION = "cg-sys-v2"
ANALYZE_PROMPT_VERSION = "cg-analyze-v3"
QNA_PROMPT_VERSION = "cg-qna-v2"

# ── Confidence & human review ────────────────────────────────────────
# Clauses scoring below this are returned with needs_human_review=True.
# Failed clauses get no score and are excluded from the overall score.
CONFIDENCE_REVIEW_THRESHOLD = 60

# ── Prompt Templates ─────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert contract analyst and legal AI assistant. Your role is to:
1. Identify risk factors in contract clauses
2. Assign a risk level (Low / Medium / High)
3. Provide a numerical risk score (0-100, where 0 = no risk)
4. Explain your reasoning clearly
5. Suggest fairer alternative language

Always respond with valid JSON only — no markdown, no commentary.
Use double quotes for all JSON keys and string values."""

ANALYZE_CLAUSE_PROMPT = """Analyze the following contract clause for legal and business risks.

Clause Title: {title}
Clause Type: {clause_type}
Clause Content:
{content}

Return a JSON object with exactly these keys:
- "risk_level": one of "Low", "Medium", or "High"
- "risk_score": integer from 0 (no risk) to 100 (extremely risky)
- "risk_factors": list of strings describing specific risks found
- "explanation": a brief (2-4 sentence) plain-language explanation of the risks
- "suggested_alternative": a rewritten version of the clause that is fairer/balanced
- "missing_protections": list of strings — protections that should exist but are absent

JSON:"""

ANSWER_QUESTION_PROMPT = """You are reviewing a contract. Answer the user's question based ONLY on the relevant contract clauses below.

Relevant Contract Clauses:
{contract_text}

User Question: {question}

Answer based ONLY on these clauses. Be concise (2-4 sentences). If the contract does not explicitly address this question, say: 'The contract does not explicitly address this.'  Plain text, no JSON needed."""

# ── All-providers-down fallback messages (sanitized — no raw errors) ─

QUOTA_EXHAUSTED_MSG = (
    "AI analysis is temporarily unavailable. "
    "Please retry in a minute or review this clause manually."
)
QNA_EXHAUSTED_MSG = (
    "Sorry, the AI analysis service is temporarily unavailable. "
    "Please try again in a minute."
)

# Groq model IDs this service knows how to route. Model names are never
# passed across providers: a non-Groq selector must not become a Groq model.
GROQ_MODEL_IDS = {
    "qwen/qwen3.8-27b",
}
SUPPORTED_PROVIDERS = {"groq", "groq_120b", "groq_8b", "ollama"}

# Patterns that indicate daily-quota exhaustion (not a per-minute limit).
# "billing" and a bare "per day" are deliberately absent: Groq includes
# billing/upgrade links in ordinary TPM 429s, and treating those as a
# day-long reset disables every provider until UTC midnight.
DAILY_QUOTA_PATTERNS = (
    "tokens per day", "requests per day", "tpd", "rpd",
    "daily quota", "daily limit",
)
PER_MINUTE_PATTERNS = (
    "tokens per minute", "requests per minute", "output tokens per minute",
    "tpm", "otpm", "rpm",
)
RATE_LIMIT_PATTERNS = (
    "rate limit", "too many requests", "tokens per minute",
    "requests per minute", "retry after",
)
NON_RETRYABLE_KINDS = {"daily_quota", "invalid_model", "auth", "bad_request"}


class ProviderError(RuntimeError):
    """Classified provider failure used for retry, fallback, and circuit state."""

    def __init__(
        self,
        message: str,
        *,
        kind: str = "unknown",
        provider: Optional[str] = None,
        retry_after: Optional[float] = None,
        status_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.provider = provider
        self.retry_after = retry_after
        self.status_code = status_code


class ClauseAnalysisError(RuntimeError):
    """Raised when a clause cannot be scored and must be marked as failed."""


@dataclass
class _ProviderState:
    """Per-provider cooldown and circuit-breaker state."""

    consecutive_failures: int = 0
    open_until: float = 0.0          # monotonic clock
    daily_reset_at: float = 0.0      # wall clock (UTC midnight)
    half_open: bool = False


@dataclass
class _TokenReservation:
    """One estimated token charge inside a provider's rolling minute."""

    provider: str
    tokens: int
    created_at: float
    released: bool = False


def _next_utc_midnight_ts() -> float:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    return tomorrow.timestamp()


def _exception_status(exc: Exception) -> Optional[int]:
    for attr in ("status_code", "http_status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int):
        return value
    value = getattr(exc, "code", None)
    if isinstance(value, int):
        return value
    text = str(exc)
    match = re.search(
        r"\b(?:error code|status(?: code)?|http)\D{0,8}(4\d\d|5\d\d)\b",
        text, re.IGNORECASE,
    )
    if match:
        return int(match.group(1))
    match = re.search(r"\b(429|401|403|404|400|422|500|502|503|504)\b", text)
    return int(match.group(1)) if match else None


def _retry_after_seconds(exc: Exception) -> Optional[float]:
    value = getattr(exc, "retry_after", None)
    if isinstance(value, (int, float)):
        return float(value)
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers:
        value = headers.get("retry-after") or headers.get("Retry-After")
        try:
            return float(value)
        except (TypeError, ValueError):
            pass
    match = re.search(r"retry[\s-]*after\D{0,12}(\d+(?:\.\d+)?)", str(exc), re.IGNORECASE)
    return float(match.group(1)) if match else None


def _is_daily_quota_message(text: str) -> bool:
    """True only for explicit day-level exhaustion, never for TPM/RPM 429s.

    Groq's per-minute 429 body often contains a billing/upgrade link and
    sometimes the words "per day" in surrounding text. A per-minute signal
    always wins so a transient burst cannot disable a provider until midnight.
    """
    if any(pattern in text for pattern in PER_MINUTE_PATTERNS):
        return False
    return any(pattern in text for pattern in DAILY_QUOTA_PATTERNS)


def _classify_error(exc: Exception, provider: str) -> ProviderError:
    """Turn an SDK/network exception into a retry decision."""
    if isinstance(exc, ProviderError):
        if exc.provider is None:
            exc.provider = provider
        return exc

    text = str(exc).lower()
    status = _exception_status(exc)
    retry_after = _retry_after_seconds(exc)

    if status in (401, 403) or "invalid api key" in text or "authentication" in text:
        kind = "auth"
    elif (
        status == 404
        or "model_not_found" in text
        or "model not found" in text
        or "does not exist" in text
        or "decommissioned" in text
    ):
        kind = "invalid_model"
    elif status == 429 or any(pattern in text for pattern in RATE_LIMIT_PATTERNS):
        kind = "daily_quota" if _is_daily_quota_message(text) else "rate_limit"
    elif _is_daily_quota_message(text):
        kind = "daily_quota"
    elif status in (400, 422):
        kind = "bad_request"
    elif status is not None and 500 <= status < 600:
        kind = "server"
    elif "timeout" in text or "timed out" in text or "deadline" in text:
        kind = "timeout"
    elif "quota" in text:
        # Ambiguous quota wording: retry briefly instead of disabling for a day.
        kind = "rate_limit"
    else:
        kind = "unknown"

    return ProviderError(
        str(exc), kind=kind, provider=provider,
        retry_after=retry_after, status_code=status,
    )


class ContractAnalyzer:
    """LLM-powered contract analysis with multi-provider routing."""

    def __init__(self) -> None:
        self._groq_client: Any = None
        self._provider_states: Dict[str, _ProviderState] = {}
        self._state_lock = threading.Lock()
        self._token_reservations: List[_TokenReservation] = []
        self._token_lock = threading.Lock()
        self._call_log: List[str] = []  # track which providers served each call

    def reset_state(self) -> None:
        """Clear provider cooldowns and request-scoped call logging."""
        with self._state_lock:
            self._provider_states.clear()
            self._call_log.clear()
        with self._token_lock:
            self._token_reservations.clear()

    @property
    def _daily_exhausted(self) -> Set[str]:
        """Backward-compatible view of providers cooling down on daily quota."""
        now = time.time()
        with self._state_lock:
            return {
                provider for provider, state in self._provider_states.items()
                if state.daily_reset_at > now
            }

    @_daily_exhausted.setter
    def _daily_exhausted(self, providers: Set[str]) -> None:
        with self._state_lock:
            for state in self._provider_states.values():
                state.daily_reset_at = 0.0
            for provider in providers:
                state = self._provider_states.setdefault(provider, _ProviderState())
                state.daily_reset_at = _next_utc_midnight_ts()

    # ── Provider Initialization ──────────────────────────────────

    def _init_groq(self):
        if self._groq_client is None and settings.has_groq:
            from groq import Groq
            try:
                # Disable the SDK's own 429 retries. It sleeps for the full
                # Retry-After (sometimes 40s+) inside one clause while holding
                # a provider lane. Our scheduler needs to see the failure
                # immediately so it can fall through or pace the next call.
                self._groq_client = Groq(
                    api_key=settings.GROQ_API_KEY,
                    timeout=settings.LLM_REQUEST_TIMEOUT,
                    max_retries=0,
                )
            except TypeError:
                # Older groq SDKs do not accept the timeout/max_retries kwargs.
                try:
                    self._groq_client = Groq(
                        api_key=settings.GROQ_API_KEY,
                        timeout=settings.LLM_REQUEST_TIMEOUT,
                    )
                except TypeError:
                    self._groq_client = Groq(api_key=settings.GROQ_API_KEY)

    # ── Provider state / circuit breaker ─────────────────────────

    def _is_provider_available(self, provider: str) -> bool:
        now_mono = time.monotonic()
        now_wall = time.time()
        with self._state_lock:
            state = self._provider_states.get(provider)
            if state is None:
                return True
            if state.daily_reset_at > now_wall:
                return False
            if state.open_until > now_mono:
                return False
            # After a cooldown, let exactly one probe through.
            if (
                state.consecutive_failures >= settings.LLM_CIRCUIT_FAILURE_THRESHOLD
                and state.open_until
            ):
                if state.half_open:
                    return False
                state.half_open = True
            return True

    def _record_success(self, provider: str) -> None:
        with self._state_lock:
            state = self._provider_states.setdefault(provider, _ProviderState())
            state.consecutive_failures = 0
            state.open_until = 0.0
            state.daily_reset_at = 0.0
            state.half_open = False

    def _record_failure(self, provider: str, error: ProviderError) -> None:
        now_mono = time.monotonic()
        with self._state_lock:
            state = self._provider_states.setdefault(provider, _ProviderState())
            state.half_open = False
            if error.kind == "daily_quota":
                state.daily_reset_at = _next_utc_midnight_ts()
                state.consecutive_failures = 0
                return
            if error.kind in ("invalid_model", "auth", "bad_request"):
                # Retrying cannot fix configuration/model errors.
                state.open_until = max(state.open_until, now_mono + 300.0)
                return
            state.consecutive_failures += 1
            if error.kind == "rate_limit":
                cooldown = error.retry_after or settings.LLM_RATE_LIMIT_COOLDOWN
                # Respect the provider's retry-after, but do not park a lane
                # for longer than the configured transient cooldown.
                ceiling = max(5.0, float(settings.LLM_RATE_LIMIT_COOLDOWN))
                cooldown = max(2.0, min(float(cooldown), ceiling))
                state.open_until = max(state.open_until, now_mono + cooldown)
            elif state.consecutive_failures >= settings.LLM_CIRCUIT_FAILURE_THRESHOLD:
                state.open_until = max(
                    state.open_until, now_mono + settings.LLM_CIRCUIT_COOLDOWN,
                )

    def _clear_daily_exhausted_if_needed(self) -> None:
        """Expire daily-quota cooldowns after UTC midnight."""
        now = time.time()
        with self._state_lock:
            for state in self._provider_states.values():
                if state.daily_reset_at and state.daily_reset_at <= now:
                    state.daily_reset_at = 0.0

    # ── Per-provider token pacing ────────────────────────────────
    # Groq's free plan caps each model at 8K tokens/minute. A burst of 31
    # clause calls otherwise stampedes the limit, so reserve estimated tokens
    # locally and let the scheduler wait for the rolling minute to recover.

    @staticmethod
    def _estimate_tokens(system: str, user_message: str, max_tokens: int) -> int:
        """Conservative estimate of prompt + requested output tokens.

        Groq's per-minute token gate counts the requested ``max_tokens`` as
        well as the prompt, so reserving a capped completion estimate lets
        bursts slip past the local pacing and turn into hard 429s.
        """
        prompt_tokens = (len(system) + len(user_message)) // 4
        completion_tokens = max(1, int(max_tokens))
        return max(80, prompt_tokens + completion_tokens + 40)

    def _prune_token_window(self, now: float) -> None:
        cutoff = now - 60.0
        self._token_reservations = [
            reservation for reservation in self._token_reservations
            if not reservation.released and reservation.created_at > cutoff
        ]

    def _reserve_tokens(
        self, provider: str, tokens: int,
    ) -> tuple:
        """Reserve tokens in the provider's rolling minute.

        Returns ``(wait_seconds, reservation)``. A positive wait means the
        caller should try another lane or sleep before retrying.
        """
        limit = max(0, int(settings.LLM_TPM_LIMIT))
        if limit <= 0:
            return 0.0, _TokenReservation(provider, 0, time.monotonic())

        now = time.monotonic()
        with self._token_lock:
            self._prune_token_window(now)
            used = sum(
                r.tokens for r in self._token_reservations
                if r.provider == provider and not r.released
            )
            if used + tokens <= limit:
                reservation = _TokenReservation(provider, tokens, now)
                self._token_reservations.append(reservation)
                return 0.0, reservation

            # Find the earliest moment enough old reservations expire.
            provider_rows = sorted(
                (r for r in self._token_reservations
                 if r.provider == provider and not r.released),
                key=lambda r: r.created_at,
            )
            running = used
            for row in provider_rows:
                running -= row.tokens
                if running + tokens <= limit:
                    return max(0.05, 60.0 - (now - row.created_at)), None
            return 1.0, None

    def _release_reservation(self, reservation: Optional[_TokenReservation]) -> None:
        if reservation is None or reservation.tokens == 0:
            return
        with self._token_lock:
            reservation.released = True

    def _provider_wait_seconds(self, provider: str) -> float:
        """How long until a cooling-down provider can accept a call."""
        now_mono = time.monotonic()
        now_wall = time.time()
        with self._state_lock:
            state = self._provider_states.get(provider)
            if state is None:
                return 0.0
            if state.daily_reset_at > now_wall:
                return state.daily_reset_at - now_wall
            if state.open_until > now_mono:
                return state.open_until - now_mono
        return 0.0

    # Backward-compatible alias used by older callers/tests.
    def _mark_daily_exhausted(self, provider: str) -> None:
        self._record_failure(
            provider,
            ProviderError("daily quota", kind="daily_quota", provider=provider),
        )

    @classmethod
    def _is_daily_quota_error(cls, error: Exception) -> bool:
        """Check if an exception indicates daily-quota exhaustion."""
        return _is_daily_quota_message(str(error).lower())

    # ── Retry helpers ────────────────────────────────────────────

    @staticmethod
    def _attempt_timeout(deadline: Optional[float]) -> float:
        """Cap one network attempt so it cannot overrun the provider budget."""
        timeout = settings.LLM_REQUEST_TIMEOUT
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderError("LLM deadline exceeded", kind="timeout")
            timeout = min(timeout, remaining)
        return max(1.0, timeout)

    @staticmethod
    def _retry_delay(attempt: int, error: ProviderError) -> float:
        if error.retry_after is not None:
            return max(0.0, min(float(error.retry_after), 10.0))
        return min(2.0 ** attempt + random.uniform(0.0, 0.25), 8.0)

    @staticmethod
    def _sleep_with_deadline(seconds: float, deadline: Optional[float]) -> None:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderError("LLM deadline exceeded", kind="timeout")
            seconds = min(seconds, remaining)
        if seconds > 0:
            time.sleep(seconds)
        if deadline is not None and time.monotonic() >= deadline:
            raise ProviderError("LLM deadline exceeded", kind="timeout")

    @staticmethod
    def _provider_model(provider: str) -> Optional[str]:
        """Return the Groq model bound to a provider lane."""
        if provider == "groq":
            return settings.GROQ_MODEL
        if provider == "groq_120b":
            return settings.GROQ_FALLBACK_MODEL
        if provider == "groq_8b":
            return settings.GROQ_LIGHT_MODEL
        return None

    @classmethod
    def _provider_for_model(cls, model: str) -> Optional[str]:
        for provider in ("groq", "groq_120b", "groq_8b"):
            if cls._provider_model(provider) == model:
                return provider
        return None

    def _ordered_providers(self, model: Optional[str]) -> List[str]:
        providers = [
            p.strip() for p in settings.PROVIDER_ORDER.split(",")
            if p.strip() in SUPPORTED_PROVIDERS
        ]
        if not providers:
            providers = ["groq"]
        if model in GROQ_MODEL_IDS:
            target = self._provider_for_model(model)
            if target:
                if target in providers:
                    providers.remove(target)
                providers.insert(0, target)
        return providers

    # ── Multi-provider call ──────────────────────────────────────

    def _call_llm(
        self,
        system: str,
        user_message: str,
        temperature: float = 0.2,
        max_tokens: int = 700,
        model: Optional[str] = None,
        validator: Optional[Callable[[str], bool]] = None,
    ) -> str:
        """
        Route through providers in settings.PROVIDER_ORDER.

        Each provider lane is paced against its own rolling token window, so
        concurrent clauses queue instead of turning into a wall of 429s.
        Transient failures fall through to the next lane, then wait for the
        earliest lane to recover.

        Raises:
            ProviderError: If no provider can serve the request.
        """
        deadline = time.monotonic() + settings.LLM_TOTAL_TIMEOUT
        self._clear_daily_exhausted_if_needed()
        providers_list = self._ordered_providers(model)
        estimated_tokens = self._estimate_tokens(system, user_message, max_tokens)

        last_error: Optional[ProviderError] = None
        # A full 60-second token window can need several 10-second checks
        # before a lane has room. Four rounds failed a valid 9-clause run.
        max_rounds = max(8, int(settings.LLM_MAX_RETRIES) + 7)

        for round_number in range(max_rounds):
            if time.monotonic() >= deadline:
                break

            retryable_seen = False
            wait_hint = 0.0

            for index, provider_name in enumerate(providers_list):
                if time.monotonic() >= deadline:
                    break

                if not self._is_provider_available(provider_name):
                    wait_hint = max(wait_hint, self._provider_wait_seconds(provider_name))
                    logger.debug("Provider '%s' cooling down, skipping.", provider_name)
                    continue

                token_wait, reservation = self._reserve_tokens(
                    provider_name, estimated_tokens,
                )
                if token_wait > 0:
                    wait_hint = max(wait_hint, token_wait)
                    retryable_seen = True
                    logger.debug(
                        "Provider '%s' token budget full; waiting %.1fs.",
                        provider_name, token_wait,
                    )
                    continue

                now = time.monotonic()
                remaining = deadline - now
                if remaining <= 0:
                    self._release_reservation(reservation)
                    break

                # Reserve time for fallbacks instead of letting one slow
                # provider consume the whole request budget.
                remaining_providers = len(providers_list) - index
                if remaining_providers > 1:
                    provider_budget = max(
                        settings.LLM_REQUEST_TIMEOUT, remaining * 0.6,
                    )
                else:
                    provider_budget = remaining
                provider_deadline = min(deadline, now + provider_budget)

                try:
                    result = self._call_single_provider(
                        provider_name, system, user_message,
                        temperature, max_tokens, model,
                        deadline=provider_deadline,
                    )
                    if validator is not None:
                        try:
                            usable = validator(result)
                        except Exception:
                            usable = False
                        if not usable:
                            error = ProviderError(
                                "Provider returned an unusable response.",
                                kind="bad_response", provider=provider_name,
                            )
                            self._record_failure(provider_name, error)
                            # Keep the reservation: the HTTP call succeeded and
                            # Groq counted its tokens, even though the JSON was
                            # unusable. Releasing it here causes the next call
                            # to overrun the lane's real per-minute budget.
                            last_error = error
                            retryable_seen = True
                            logger.warning(
                                "Provider '%s' returned an unusable response; "
                                "trying next provider.", provider_name,
                            )
                            continue

                    logger.info("Provider '%s' succeeded.", provider_name)
                    self._record_success(provider_name)
                    self._call_log.append(provider_name)
                    return result
                except Exception as exc:
                    error = _classify_error(exc, provider_name)
                    self._record_failure(provider_name, error)
                    self._release_reservation(reservation)
                    last_error = error
                    if error.kind not in NON_RETRYABLE_KINDS:
                        retryable_seen = True
                    wait_hint = max(wait_hint, self._provider_wait_seconds(provider_name))
                    logger.warning(
                        "Provider '%s' failed (%s): %s",
                        provider_name, error.kind, str(error)[:200],
                    )

            if (
                last_error is not None
                and last_error.kind == "daily_quota"
                and not retryable_seen
                and wait_hint <= 0
            ):
                break
            if not retryable_seen and wait_hint <= 0:
                break
            if time.monotonic() >= deadline:
                break

            # Wait for the earliest cooling lane or token reset, capped so a
            # queued clause re-checks its options regularly.
            sleep_for = min(max(wait_hint, 0.5), 10.0)
            logger.debug(
                "All LLM lanes busy (round %d/%d); waiting %.1fs.",
                round_number + 1, max_rounds, sleep_for,
            )
            try:
                self._sleep_with_deadline(sleep_for, deadline)
            except ProviderError:
                break

        if last_error is not None and last_error.kind == "daily_quota":
            raise ProviderError(
                "All LLM providers are temporarily unavailable (daily quota reached).",
                kind="daily_quota",
            )
        raise ProviderError(
            "All LLM providers are temporarily unavailable.",
            kind="all_down",
        )

    def _call_single_provider(
        self,
        provider: str,
        system: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        model: Optional[str],
        deadline: Optional[float] = None,
    ) -> str:
        """Dispatch to the correct provider implementation."""
        if provider in ("groq", "groq_120b", "groq_8b"):
            if provider == "groq":
                groq_model = self._resolve_groq_model(model)
            else:
                groq_model = self._provider_model(provider)
            return self._call_groq(
                system, user_message, temperature, max_tokens,
                groq_model, deadline=deadline, provider=provider,
            )
        if provider == "ollama":
            return self._call_ollama(
                system, user_message, temperature, max_tokens, deadline=deadline,
            )
        raise ProviderError(f"Unknown provider: {provider}", kind="unknown", provider=provider)

    @staticmethod
    def _resolve_groq_model(model: Optional[str]) -> str:
        """Never pass a non-Groq selector into a Groq API call."""
        if model in GROQ_MODEL_IDS:
            return str(model)
        return settings.GROQ_MODEL

    # ── Groq ─────────────────────────────────────────────────────

    def _call_groq(
        self,
        system: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
        deadline: Optional[float] = None,
        provider: str = "groq",
    ) -> str:
        self._init_groq()
        if self._groq_client is None:
            raise ProviderError(
                "Groq client not initialized (no API key).",
                kind="auth", provider=provider,
            )

        actual_model = model or settings.GROQ_MODEL
        attempts = max(1, settings.LLM_MAX_RETRIES + 1)

        for attempt in range(attempts):
            if deadline is not None and time.monotonic() >= deadline:
                raise ProviderError(
                    "Groq deadline exceeded", kind="timeout", provider=provider,
                )
            try:
                request_timeout = self._attempt_timeout(deadline)
                request_kwargs = {
                    "model": actual_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timeout": request_timeout,
                }
                if actual_model.startswith("openai/gpt-oss"):
                    # The gpt-oss models spend part of max_tokens on hidden
                    # reasoning. At the default effort they burn 800 tokens
                    # on a 1,000-token budget and truncate the JSON. Low
                    # effort keeps reasoning near 20 tokens for these
                    # structured extraction prompts.
                    request_kwargs["reasoning_effort"] = "low"
                try:
                    completion = self._groq_client.chat.completions.create(
                        **request_kwargs,
                    )
                except TypeError:
                    # Older groq SDKs do not accept per-request timeout or
                    # reasoning_effort kwargs.
                    request_kwargs.pop("timeout", None)
                    request_kwargs.pop("reasoning_effort", None)
                    completion = self._groq_client.chat.completions.create(
                        **request_kwargs,
                    )
                content = completion.choices[0].message.content
                if content is None:
                    raise ValueError("Groq returned empty response content.")
                return content
            except Exception as exc:
                error = _classify_error(exc, provider)
                if error.kind in NON_RETRYABLE_KINDS or attempt >= attempts - 1:
                    raise error
                delay = self._retry_delay(attempt, error)
                logger.warning(
                    "%s attempt %d/%d failed (%s); retrying in %.1fs",
                    provider, attempt + 1, attempts, error.kind, delay,
                )
                self._sleep_with_deadline(delay, deadline)

        raise ProviderError("Groq call failed", kind="unknown", provider=provider)

    # ── Ollama (local dev) ──────────────────────────────────────

    def _call_ollama(
        self,
        system: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        deadline: Optional[float] = None,
    ) -> str:
        """Call local Ollama with a short timeout. Fails fast."""
        import urllib.request
        import urllib.error

        if deadline is not None and time.monotonic() >= deadline:
            raise ProviderError("Ollama deadline exceeded", kind="timeout", provider="ollama")

        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
        body = json.dumps({
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            timeout = min(3.0, self._attempt_timeout(deadline))
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data.get("message", {}).get("content", "")
                if not content:
                    raise ValueError("Ollama returned empty response.")
                return content
        except Exception as exc:
            raise _classify_error(exc, "ollama") from exc

    # ── Clause Analysis ──────────────────────────────────────────

    @staticmethod
    def _parse_quality(raw: str) -> str:
        """How cleanly the model output parsed: direct / recovered / heuristic.

        Note: reasoning models can exhaust max_tokens mid-object, leaving
        truncated JSON with no closing brace. The per-field regexes in
        _extract_fields_heuristic still recover those, so field presence
        (not brace matching) decides recovered vs heuristic.
        """
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            json.loads(text)
            return "direct"
        except json.JSONDecodeError:
            pass
        try:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                json.loads(m.group(0))
                return "recovered"
        except json.JSONDecodeError:
            pass
        has_level = bool(re.search(r'"risk_level"\s*:\s*"(\w+)"', text, re.IGNORECASE))
        has_score = bool(re.search(r'"risk_score"\s*:\s*(\d+)', text))
        if has_level and has_score:
            return "recovered"  # truncated but decision fields intact
        return "heuristic"

    @staticmethod
    def _score_confidence(parse_quality: str, content_len: int, llm_ok: bool) -> int:
        """Heuristic confidence for a clause score (0-100)."""
        if not llm_ok:
            return 40  # provider fallback: provisional score, must be reviewed
        base = {"direct": 85, "recovered": 70, "heuristic": 55}[parse_quality]
        if content_len < 120:
            base -= 10  # thin signal
        return max(40, min(98, base))

    def _has_decision_fields(self, raw: str) -> bool:
        """True only when the response contains both risk decision fields."""
        if self._parse_quality(raw) == "heuristic":
            return False
        parsed = self._parse_json(raw)
        return (
            isinstance(parsed, dict)
            and "risk_level" in parsed
            and "risk_score" in parsed
        )

    def analyze_clause(
        self,
        clause: Dict[str, str],
        model: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        title = clause.get("title", "Untitled Clause")
        content = (clause.get("content", "") or "")[:1200]  # trim to 1200 chars
        clause_type = clause.get("type", "general")
        clause_id = clause.get("id", "unknown")

        logger.info("Analyzing clause %s (%s, %d chars)...", clause_id, clause_type, len(content))

        if not content.strip():
            return self._low_risk_result("Empty clause — nothing to analyze.")

        prompt = ANALYZE_CLAUSE_PROMPT.format(title=title, clause_type=clause_type, content=content)

        try:
            raw_output = self._call_llm(
                system=SYSTEM_PROMPT, user_message=prompt,
                temperature=0.2, max_tokens=700, model=model,
                validator=self._has_decision_fields,
            )
            quality = self._parse_quality(raw_output)
            if quality == "heuristic":
                # No decision fields survived parsing. Returning Low/0 here
                # would be a fabricated score, so fail the clause instead.
                raise ClauseAnalysisError("Model returned an unreadable response.")

            result = self._parse_json(raw_output)
            result["risk_level"] = self._normalize_risk_level(result.get("risk_level", "Medium"))
            result["risk_score"] = self._normalize_risk_score(result.get("risk_score", 50))
            for lk in ("risk_factors", "missing_protections"):
                if not isinstance(result.get(lk), list):
                    result[lk] = [str(result.get(lk, ""))] if result.get(lk) else []
            confidence = self._score_confidence(quality, len(content), llm_ok=True)
            result["confidence"] = confidence
            result["needs_human_review"] = confidence < CONFIDENCE_REVIEW_THRESHOLD
            result["parse_quality"] = quality
            result["analysis_status"] = ClauseStatus.COMPLETE.value
            result["fallback_used"] = False
            logger.info("Clause %s → risk=%s, score=%d", clause_id, result.get("risk_level"), result.get("risk_score"))
            trace_log(
                "clause_scored", request_id=request_id, clause_id=clause_id,
                clause_type=clause_type, risk_level=result.get("risk_level"),
                risk_score=result.get("risk_score"), confidence=confidence,
                needs_human_review=result["needs_human_review"],
                parse_quality=quality, prompt_version=ANALYZE_PROMPT_VERSION,
                groq_model=settings.GROQ_MODEL,
            )
            return result
        except ClauseAnalysisError:
            raise
        except Exception as exc:
            error = _classify_error(exc, "llm")
            logger.warning(
                "Clause %s: analysis unavailable (%s).", clause_id, error.kind,
            )
            trace_log(
                "clause_scored", request_id=request_id, clause_id=clause_id,
                clause_type=clause_type, risk_level=None, risk_score=None,
                confidence=0, needs_human_review=True, parse_quality=ParseQuality.FAILED.value,
                llm_available=False, error_kind=error.kind,
                prompt_version=ANALYZE_PROMPT_VERSION,
                groq_model=settings.GROQ_MODEL,
            )
            raise ClauseAnalysisError(QUOTA_EXHAUSTED_MSG) from exc

    # ── Contract-Level Aggregation ──────────────────────────────

    def analyze_contract(self, clauses: List[Dict]) -> Dict[str, Any]:
        if not clauses:
            return {
                "overall_score": 0, "risk_breakdown": {"High": 0, "Medium": 0, "Low": 0},
                "high_risk_clauses": [], "total_clauses": 0, "summary": "No clauses to analyze.",
            }
        total_score = 0
        breakdown: Dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}
        high_risk: List[Dict] = []
        scored = 0
        for c in clauses:
            rl = c.get("risk_level")
            rs = c.get("risk_score")
            if rl not in ("High", "Medium", "Low") or not isinstance(rs, (int, float)):
                continue
            scored += 1
            total_score += rs
            breakdown[rl] = breakdown.get(rl, 0) + 1
            if rl == "High":
                high_risk.append({"id": c.get("id"), "title": c.get("title"), "risk_score": rs, "explanation": c.get("explanation", "")})
        overall = round(total_score / scored, 1) if scored else 0
        if overall >= 75:
            assessment = "High Risk — This contract contains significant risks that require attention before signing."
        elif overall >= 45:
            assessment = "Medium Risk — Several areas of concern. Negotiation recommended."
        else:
            assessment = "Low Risk — This contract appears generally balanced and fair."
        return {
            "overall_score": overall, "risk_breakdown": breakdown,
            "high_risk_clauses": high_risk, "total_clauses": len(clauses), "summary": assessment,
        }

    # ── Keyword Map ──────────────────────────────────────────────

    KEYWORD_MAP: Dict[str, List[str]] = {
        "absent": ["absent", "leave", "termination", "resign", "abscond"],
        "salary": ["salary", "payment", "wages", "deduction", "gratuity", "pf", "esi", "compensation", "fee"],
        "property": ["property", "asset", "equipment", "return", "hardware", "peripheral", "laptop"],
        "arbitration": ["arbitration", "dispute", "governing law", "court", "jurisdiction"],
        "permanent": ["permanent", "permanency", "contractual", "fixed-term", "temporary"],
        "client": ["client", "payment", "deploy", "transfer", "assignment"],
        "probation": ["probation", "period", "notice", "termination", "training"],
        "confidential": ["confidential", "secret", "nda", "proprietary", "intellectual", "trade secret"],
        "performance": ["performance", "appraisal", "training", "duties", "responsibilities", "obligations"],
        "modification": ["modify", "alter", "amend", "change", "waiver", "variation"],
        "indemnity": ["indemnify", "liability", "damage", "loss", "claim", "hold harmless"],
        "conflict": ["conflict", "interest", "compete", "solicit", "dual employment", "non-compete"],
        "notice": ["notice", "period", "resign", "quit", "resignation", "relieving"],
        "hours": ["hours", "overtime", "working time", "shift", "workday", "rest break", "work week"],
        "leave": ["leave", "holiday", "vacation", "sick", "annual leave", "paid time off", "pto"],
        "termination": ["termination", "fired", "dismiss", "severance", "terminate", "dismissal"],
        "benefits": ["benefit", "insurance", "medical", "health", "pension", "provident fund", "esi", "gratuity"],
        "transfer": ["transfer", "relocate", "relocation", "move", "location", "deputation"],
        "noncompete": ["non-compete", "non compete", "restrictive covenant", "competitor", "solicit", "poach"],
        "ip": ["intellectual property", "invention", "copyright", "patent", "ownership", "created", "developed"],
        "background_check": ["background", "criminal", "verification", "reference", "check", "screening"],
        "travel": ["travel", "expense", "reimbursement", "per diem", "mileage", "transport"],
        "training": ["training", "bond", "training cost", "education", "certification", "skill"],
        "moonlighting": ["moonlight", "dual employment", "outside work", "freelance", "side business"],
        "harassment": ["harassment", "discrimination", "grievance", "complaint", "workplace", "equal opportunity"],
        "remote": ["remote", "work from home", "wfh", "telecommute", "hybrid", "virtual"],
    }

    def _find_relevant_clauses(self, contract_text: str, question: str) -> str:
        if not contract_text or not question:
            return contract_text[:4000] if contract_text else ""
        ql = question.lower()
        matched_kw: List[str] = []
        for topic, kws in self.KEYWORD_MAP.items():
            if any(kw in ql for kw in kws):
                matched_kw.extend(kws)
        if not matched_kw:
            matched_kw = [w.strip().lower() for w in re.split(r"\W+", ql) if len(w) > 3]
        clauses = re.split(r"\n\s*\n", contract_text)
        if len(clauses) < 2:
            clauses = re.split(r"(?:\n|^)(?=\d+[\.\)]|ARTICLE|SECTION|Clause)", contract_text)
        scored: List[tuple] = []
        for clause in clauses:
            cl = clause.lower()
            s = sum(1 for kw in matched_kw if kw in cl)
            if s > 0:
                scored.append((s, clause.strip()))
        scored.sort(key=lambda x: x[0], reverse=True)
        budget = 8000
        selected: List[str] = []
        total = 0
        for _, cl in scored:
            if total + len(cl) <= budget:
                selected.append(cl)
                total += len(cl) + 2
            else:
                rem = budget - total
                if rem > 100:
                    selected.append(cl[:rem] + "...")
                break
        if not selected:
            return contract_text[:4000]
        result = "\n\n".join(selected)
        logger.info("Context trimmed: %d chars → %d chars (%d clauses)", len(contract_text), len(result), len(selected))
        return result

    # ── Question Answering ──────────────────────────────────────

    def answer_question(
        self,
        contract_text: str,
        question: str,
        model: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> str:
        if not contract_text.strip():
            return "No contract text available to answer questions."
        if not question.strip():
            return "Please provide a question about the contract."
        logger.info("Answering: %s", question[:80])
        relevant = self._find_relevant_clauses(contract_text, question)
        prompt = ANSWER_QUESTION_PROMPT.format(contract_text=relevant, question=question)
        try:
            answer = self._call_llm(
                system="You are a helpful legal contract assistant. Answer concisely.",
                user_message=prompt, temperature=0.3, max_tokens=300,
                model=model,
            )
            answer = answer.strip()
            if not answer:
                raise ValueError("empty answer")
            trace_log(
                "qa", request_id=request_id, question=question[:300],
                contract_chars=len(contract_text),
                retrieved_passages=len(relevant.split("\n\n")),
                retrieved_chars=len(relevant), answer_chars=len(answer),
                requested_model=model,
                prompt_version=QNA_PROMPT_VERSION,
                groq_model=settings.GROQ_MODEL,
            )
            return answer
        except Exception:
            trace_log(
                "qa", request_id=request_id, question=question[:300],
                contract_chars=len(contract_text), retrieved_chars=len(relevant),
                answer_chars=0, llm_available=False, requested_model=model,
                prompt_version=QNA_PROMPT_VERSION,
                groq_model=settings.GROQ_MODEL,
            )
            return QNA_EXHAUSTED_MSG

    # ── JSON Parsing ────────────────────────────────────────────

    def _parse_json_list(self, raw: str) -> Any:
        """Parse a JSON array, salvaging complete objects from a cut-off reply.

        Reasoning models sometimes run out of max_tokens mid-array. Returning
        None for the whole response throws away every complete finding before
        the cut, so trim back to the last closed object and retry.
        """
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, (list, dict)):
                return parsed
        except json.JSONDecodeError:
            pass

        start = text.find("[")
        if start < 0:
            return self._parse_json(text)
        body = text[start:]
        last_brace = body.rfind("}")
        while last_brace > 0:
            candidate = body[:last_brace + 1] + "]"
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                last_brace = body.rfind("}", 0, last_brace)
                continue
            last_brace = body.rfind("}", 0, last_brace)
        return self._parse_json(text)

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        return self._extract_fields_heuristic(raw)

    def _extract_fields_heuristic(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        rl = re.search(r'"risk_level"\s*:\s*"(\w+)"', text, re.IGNORECASE)
        if rl:
            result["risk_level"] = self._normalize_risk_level(rl.group(1))
        rs = re.search(r'"risk_score"\s*:\s*(\d+)', text)
        if rs:
            result["risk_score"] = int(rs.group(1))
        expl = re.search(r'"explanation"\s*:\s*"([^"]+)"', text, re.DOTALL)
        if expl:
            result["explanation"] = expl.group(1)[:500]
        alt = re.search(r'"suggested_alternative"\s*:\s*"([^"]+)"', text, re.DOTALL)
        if alt:
            result["suggested_alternative"] = alt.group(1)[:1000]
        rf = re.search(r'"risk_factors"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if rf:
            result["risk_factors"] = re.findall(r'"([^"]+)"', rf.group(1)) or ["Unable to parse."]
        mp = re.search(r'"missing_protections"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if mp:
            result["missing_protections"] = re.findall(r'"([^"]+)"', mp.group(1))
        for k in ("risk_level", "risk_score", "risk_factors", "explanation", "suggested_alternative", "missing_protections"):
            if k not in result:
                result[k] = self._default_value(k)
        return result

    @staticmethod
    def _normalize_risk_level(value: Any) -> str:
        if isinstance(value, str):
            c = value.strip().title()
            if c in ("Low", "Medium", "High"):
                return c
            if "high" in c.lower():
                return "High"
            if "med" in c.lower():
                return "Medium"
        return "Low"

    @staticmethod
    def _normalize_risk_score(value: Any) -> int:
        try:
            return max(0, min(100, int(float(str(value)))))
        except (ValueError, TypeError):
            return 50

    @staticmethod
    def _default_value(key: str) -> Any:
        return {
            "risk_level": "Low", "risk_score": 0, "risk_factors": [],
            "explanation": "", "suggested_alternative": "", "missing_protections": [],
        }.get(key, "")

    @staticmethod
    def _low_risk_result(message: str) -> Dict[str, Any]:
        return {
            "risk_level": "Low", "risk_score": 0, "risk_factors": [],
            "explanation": message, "suggested_alternative": "", "missing_protections": [],
            "confidence": 95, "needs_human_review": False,
            "parse_quality": ParseQuality.EMPTY.value,
            "analysis_status": ClauseStatus.COMPLETE.value,
            "fallback_used": False,
        }


analyzer = ContractAnalyzer()
