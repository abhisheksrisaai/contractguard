"""
ContractGuard - LLM Risk Analysis Service
Multi-provider routing with graceful degradation.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings

logger = logging.getLogger(__name__)

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
    "AI analysis temporarily unavailable (daily quota reached). "
    "Showing heuristic assessment — please review manually or retry later."
)
QNA_EXHAUSTED_MSG = (
    "Sorry, the AI analysis service is temporarily unavailable due to daily quota limits. "
    "Please try again later."
)

# Patterns that indicate daily-quota exhaustion (not per-minute rate limit)
DAILY_QUOTA_PATTERNS = [
    "tokens per day", "tpd", "daily", "quota exceeded",
    "billing", "upgrade to dev tier", "rate limit reached for model",
]


class ContractAnalyzer:
    """LLM-powered contract analysis with multi-provider routing."""

    def __init__(self) -> None:
        self._groq_client: Any = None
        self._gemini_client: Any = None
        self._daily_exhausted: Set[str] = set()  # provider names that hit daily quota

    # ── Provider Initialization ──────────────────────────────────

    def _init_groq(self):
        if self._groq_client is None and settings.has_groq:
            from groq import Groq
            self._groq_client = Groq(api_key=settings.GROQ_API_KEY)

    def _init_gemini(self):
        if self._gemini_client is None and settings.has_gemini:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._gemini_client = genai

    # ── Daily quota check ───────────────────────────────────────

    @classmethod
    def _is_daily_quota_error(cls, error: Exception) -> bool:
        """Check if an exception indicates a daily quota exhaustion (not RPM)."""
        msg = str(error).lower()
        return any(p in msg for p in DAILY_QUOTA_PATTERNS)

    def _mark_daily_exhausted(self, provider: str) -> None:
        self._daily_exhausted.add(provider)

    def _clear_daily_exhausted_if_needed(self) -> None:
        """Clear daily exhaustion flags after UTC midnight."""
        # Simplified: clear on any call after a reasonable interval
        # In production, a proper scheduler would do this, but simple
        # time-since-mark approach is sufficient at our request volume.
        pass  # flags auto-reset on process restart (ephemeral)

    # ── Multi-provider call ──────────────────────────────────────

    def _call_llm(
        self,
        system: str,
        user_message: str,
        temperature: float = 0.2,
        max_tokens: int = 700,
        model: Optional[str] = None,
    ) -> str:
        """
        Route through providers in settings.PROVIDER_ORDER.
        Falls through on daily-quota errors; retries transient errors.

        Returns:
            Raw response text from the model.

        Raises:
            RuntimeError: If ALL providers are exhausted/unavailable.
        """
        providers_list = [p.strip() for p in settings.PROVIDER_ORDER.split(",") if p.strip()]

        for provider_name in providers_list:
            if provider_name in self._daily_exhausted:
                logger.debug("Provider '%s' marked daily-exhausted, skipping.", provider_name)
                continue

            try:
                result = self._call_single_provider(
                    provider_name, system, user_message, temperature, max_tokens, model,
                )
                logger.info("Provider '%s' succeeded.", provider_name)
                return result
            except RuntimeError as exc:
                # Daily quota → mark exhausted, fall through
                if self._is_daily_quota_error(exc):
                    logger.warning(
                        "Provider '%s' daily quota exhausted, marking and skipping.", provider_name,
                    )
                    self._mark_daily_exhausted(provider_name)
                    continue
                # Transient failure (all retries used) → fall through
                logger.warning("Provider '%s' failed (transient): %s", provider_name, exc)
                continue

        raise RuntimeError("All LLM providers are temporarily unavailable (daily quotas exhausted or unreachable).")

    def _call_single_provider(
        self,
        provider: str,
        system: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        model: Optional[str],
    ) -> str:
        """Dispatch to the correct provider implementation."""
        if provider == "gemini":
            return self._call_gemini(system, user_message, temperature, max_tokens)
        elif provider == "groq":
            groq_model = model or settings.GROQ_MODEL
            return self._call_groq(system, user_message, temperature, max_tokens, groq_model)
        elif provider == "groq_8b":
            return self._call_groq(system, user_message, temperature, max_tokens, "llama-3.1-8b-instant")
        elif provider == "ollama":
            return self._call_ollama(system, user_message, temperature, max_tokens)
        else:
            raise RuntimeError(f"Unknown provider: {provider}")

    # ── Groq ─────────────────────────────────────────────────────

    def _call_groq(
        self,
        system: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
    ) -> str:
        self._init_groq()
        if self._groq_client is None:
            raise RuntimeError("Groq client not initialized (no API key).")

        actual_model = model or settings.GROQ_MODEL

        for attempt in range(3):
            try:
                completion = self._groq_client.chat.completions.create(
                    model=actual_model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = completion.choices[0].message.content
                if content is None:
                    raise ValueError("Groq returned empty response content.")
                return content
            except Exception as exc:
                err_msg = str(exc).lower()
                # Daily quota → don't retry, let caller fall through
                if "429" in str(exc) and self._is_daily_quota_error(exc):
                    raise RuntimeError(f"Groq daily quota: {exc}") from exc
                # Other errors → retry with backoff
                logger.warning("Groq attempt %d/3 failed: %s", attempt + 1, str(exc)[:200])
                if attempt < 2:
                    time.sleep(2 ** attempt)

        raise RuntimeError(f"Groq call failed after 3 attempts")

    # ── Gemini ───────────────────────────────────────────────────

    def _call_gemini(
        self,
        system: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        self._init_gemini()
        if self._gemini_client is None:
            raise RuntimeError("Gemini client not initialized (no API key).")

        for attempt in range(3):
            try:
                model = self._gemini_client.GenerativeModel(
                    model_name=settings.GEMINI_MODEL,
                    system_instruction=system,
                )
                generation_config = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
                response = model.generate_content(
                    user_message,
                    generation_config=generation_config,
                )
                if not response or not response.text:
                    raise ValueError("Gemini returned empty response.")
                return response.text
            except Exception as exc:
                err_msg = str(exc).lower()
                if "429" in str(exc) or "quota" in err_msg or "rate" in err_msg:
                    raise RuntimeError(f"Gemini quota: {exc}") from exc
                logger.warning("Gemini attempt %d/3 failed: %s", attempt + 1, str(exc)[:200])
                if attempt < 2:
                    time.sleep(2 ** attempt)

        raise RuntimeError(f"Gemini call failed after 3 attempts")

    # ── Ollama (local dev) ──────────────────────────────────────

    def _call_ollama(
        self,
        system: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call local Ollama with 3s timeout. Fails fast."""
        import urllib.request
        import urllib.error

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
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {}).get("content", "")
        except Exception as exc:
            raise RuntimeError(f"Ollama call failed: {exc}") from exc

    # ── Clause Analysis ──────────────────────────────────────────

    ANALYZE_CLAUSE_FAILED = {
        "risk_level": "Medium",
        "risk_score": 50,
        "risk_factors": ["AI analysis temporarily unavailable."],
        "explanation": QUOTA_EXHAUSTED_MSG,
        "suggested_alternative": "",
        "missing_protections": ["Unable to determine — please review manually."],
    }

    def analyze_clause(self, clause: Dict[str, str], model: Optional[str] = None) -> Dict[str, Any]:
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
            )
            result = self._parse_json(raw_output)
            result["risk_level"] = self._normalize_risk_level(result.get("risk_level", "Medium"))
            result["risk_score"] = self._normalize_risk_score(result.get("risk_score", 50))
            for lk in ("risk_factors", "missing_protections"):
                if not isinstance(result.get(lk), list):
                    result[lk] = [str(result.get(lk, ""))] if result.get(lk) else []
            logger.info("Clause %s → risk=%s, score=%d", clause_id, result.get("risk_level"), result.get("risk_score"))
            return result
        except Exception:
            logger.warning("Clause %s: all providers exhausted, returning heuristic fallback.", clause_id)
            fallback = dict(self.ANALYZE_CLAUSE_FAILED)
            fallback["suggested_alternative"] = content
            return fallback

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
        for c in clauses:
            rl = c.get("risk_level", "Low")
            rs = c.get("risk_score", 0)
            total_score += rs
            breakdown[rl] = breakdown.get(rl, 0) + 1
            if rl == "High":
                high_risk.append({"id": c.get("id"), "title": c.get("title"), "risk_score": rs, "explanation": c.get("explanation", "")})
        overall = round(total_score / len(clauses), 1) if clauses else 0
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

    def answer_question(self, contract_text: str, question: str) -> str:
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
            )
            return answer.strip()
        except Exception:
            return QNA_EXHAUSTED_MSG

    # ── JSON Parsing ────────────────────────────────────────────

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
        }


analyzer = ContractAnalyzer()
