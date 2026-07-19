"""
ContractGuard - LLM Risk Analysis Service

Provides:
- Clause-level risk analysis via Groq LLM
- Whole-contract aggregation & scoring
- Contract Q&A
- Robust JSON parsing with fallback extraction
"""

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from groq import Groq

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


class ContractAnalyzer:
    """
    LLM-powered contract analysis using Groq.

    Handles:
    - Individual clause risk analysis
    - Whole-contract risk aggregation
    - Contract Q&A
    """

    def __init__(self) -> None:
        self._client: Optional[Groq] = None

    @property
    def client(self) -> Groq:
        """Lazy-initialize Groq client with API key validation."""
        if self._client is None:
            settings.validate_groq_key()
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    # ── Clause-Level Analysis ─────────────────────────────────────

    def analyze_clause(self, clause: Dict[str, str]) -> Dict[str, Any]:
        """
        Analyze a single clause for risks.

        Args:
            clause: Dict with keys 'id', 'title', 'content', 'type'.

        Returns:
            Dict with risk_level, risk_score, risk_factors, explanation,
            suggested_alternative, and missing_protections.
        """
        title = clause.get("title", "Untitled Clause")
        content = clause.get("content", "")
        clause_type = clause.get("type", "general")
        clause_id = clause.get("id", "unknown")

        logger.info("Analyzing clause %s (%s)...", clause_id, clause_type)

        if not content.strip():
            return self._low_risk_result("Empty clause — nothing to analyze.")

        prompt = ANALYZE_CLAUSE_PROMPT.format(
            title=title,
            clause_type=clause_type,
            content=content,
        )

        try:
            raw_output = self._call_groq(
                system=SYSTEM_PROMPT,
                user_message=prompt,
                temperature=0.2,
                max_tokens=1024,
            )
            result = self._parse_json(raw_output)

            # Validate required keys
            required_keys = [
                "risk_level", "risk_score", "risk_factors",
                "explanation", "suggested_alternative", "missing_protections",
            ]
            for key in required_keys:
                if key not in result:
                    result[key] = self._default_value(key)

            # Normalize risk_level
            result["risk_level"] = self._normalize_risk_level(result["risk_level"])

            # Normalize risk_score to int 0-100
            result["risk_score"] = self._normalize_risk_score(result["risk_score"])

            # Ensure list fields are lists
            for list_key in ("risk_factors", "missing_protections"):
                if not isinstance(result[list_key], list):
                    result[list_key] = [str(result[list_key])] if result[list_key] else []

            logger.info("Clause %s → risk=%s, score=%d", clause_id, result["risk_level"], result["risk_score"])
            return result

        except Exception as exc:
            logger.error("Clause analysis failed for %s: %s", clause_id, exc)
            return {
                "risk_level": "Medium",
                "risk_score": 50,
                "risk_factors": ["Analysis failed — manual review recommended."],
                "explanation": f"Automated analysis could not be completed: {exc}",
                "suggested_alternative": content,
                "missing_protections": ["Unable to determine — please review manually."],
            }

    # ── Contract-Level Aggregation ────────────────────────────────

    def analyze_contract(self, clauses: List[Dict]) -> Dict[str, Any]:
        """
        Generate an overall risk report from analyzed clauses.

        Args:
            clauses: List of clause dicts (with analysis results merged in).

        Returns:
            Dict with overall_score, risk_breakdown, high_risk_clauses, summary.
        """
        if not clauses:
            return {
                "overall_score": 0,
                "risk_breakdown": {"High": 0, "Medium": 0, "Low": 0},
                "high_risk_clauses": [],
                "total_clauses": 0,
                "summary": "No clauses to analyze.",
            }

        total_score = 0
        breakdown: Dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}
        high_risk: List[Dict] = []

        for clause in clauses:
            risk_level = clause.get("risk_level", "Low")
            risk_score = clause.get("risk_score", 0)

            total_score += risk_score
            breakdown[risk_level] = breakdown.get(risk_level, 0) + 1

            if risk_level == "High":
                high_risk.append({
                    "id": clause.get("id"),
                    "title": clause.get("title"),
                    "risk_score": risk_score,
                    "explanation": clause.get("explanation", ""),
                })

        overall = round(total_score / len(clauses), 1) if clauses else 0

        # Buffered thresholds to prevent borderline flip-flopping
        if overall >= 75:
            assessment = "High Risk — This contract contains significant risks that require attention before signing."
        elif overall >= 45:
            assessment = "Medium Risk — Several areas of concern. Negotiation recommended."
        else:
            assessment = "Low Risk — This contract appears generally balanced and fair."

        return {
            "overall_score": overall,
            "risk_breakdown": breakdown,
            "high_risk_clauses": high_risk,
            "total_clauses": len(clauses),
            "summary": assessment,
        }

    # ── Smart Context Trimming ──────────────────────────────────

    # Keyword map: maps question topics to search keywords in contract
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
    }

    def _find_relevant_clauses(self, contract_text: str, question: str) -> str:
        """
        Extract only the clauses relevant to the user's question.

        Strategy:
        1. Match question against keyword_map to identify topic
        2. Split contract into clauses (by double-newlines or numbered headers)
        3. Score each clause against matched keywords
        4. Return top matching clauses within 8000 char budget
        """
        if not contract_text or not question:
            return contract_text[:4000] if contract_text else ""

        question_lower = question.lower()

        # Find matching keywords from the map
        matched_keywords: List[str] = []
        for topic, keywords in self.KEYWORD_MAP.items():
            if any(kw in question_lower for kw in keywords):
                matched_keywords.extend(keywords)

        # If no keyword match, use words from question as fallback
        if not matched_keywords:
            matched_keywords = [w.strip().lower() for w in re.split(r"\W+", question_lower) if len(w) > 3]

        # Split contract into clauses
        clauses = re.split(r"\n\s*\n", contract_text)
        if len(clauses) < 2:
            # Try splitting by numbered headers
            clauses = re.split(r"(?:\n|^)(?=\d+[\.\)]|ARTICLE|SECTION|Clause)", contract_text)

        # Score each clause by keyword match count
        scored: List[tuple] = []
        for clause in clauses:
            clause_lower = clause.lower()
            score = sum(1 for kw in matched_keywords if kw in clause_lower)
            if score > 0:
                scored.append((score, clause.strip()))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Build trimmed context with 8000 char budget
        budget = 8000
        selected: List[str] = []
        total = 0
        for _, clause in scored:
            if total + len(clause) <= budget:
                selected.append(clause)
                total += len(clause) + 2  # +2 for separator
            else:
                # Fit partial if room
                remaining = budget - total
                if remaining > 100:
                    selected.append(clause[:remaining] + "...")
                break

        if not selected:
            # Fallback: return first 4000 chars
            return contract_text[:4000]

        result = "\n\n".join(selected)
        logger.info(
            "Context trimmed: %d chars → %d chars (%d clauses matched)",
            len(contract_text), len(result), len(selected),
        )
        return result

    # ── Question Answering ────────────────────────────────────────

    def answer_question(self, contract_text: str, question: str) -> str:
        """
        Answer a user's question about the contract using smart context trimming.

        Args:
            contract_text: Full contract text.
            question: User's question.

        Returns:
            Plain-text answer (2-4 sentences).
        """
        if not contract_text.strip():
            return "No contract text available to answer questions."

        if not question.strip():
            return "Please provide a question about the contract."

        logger.info("Answering question: %s", question[:80])

        # Smart context trimming
        relevant = self._find_relevant_clauses(contract_text, question)

        prompt = ANSWER_QUESTION_PROMPT.format(
            contract_text=relevant,
            question=question,
        )

        try:
            answer = self._call_groq(
                system="You are a helpful legal contract assistant. Answer concisely.",
                user_message=prompt,
                temperature=0.3,
                max_tokens=300,
            )
            return answer.strip()
        except Exception as exc:
            logger.error("Q&A failed: %s", exc)
            return f"Sorry, I couldn't answer that question due to a technical issue: {exc}"

    # ── Internal Helpers ──────────────────────────────────────────

    def _call_groq(
        self,
        system: str,
        user_message: str,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        retries: int = 2,
    ) -> str:
        """
        Call Groq API with retry logic.

        Args:
            system: System prompt.
            user_message: User message / prompt.
            temperature: Sampling temperature.
            max_tokens: Max tokens in response.
            retries: Number of retry attempts on failure.

        Returns:
            Raw response text from the model.

        Raises:
            RuntimeError: If all retries are exhausted.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, retries + 2):
            try:
                completion = self.client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                # Extract response content
                content = completion.choices[0].message.content
                if content is None:
                    raise ValueError("Groq returned empty response content.")
                return content

            except Exception as exc:
                last_error = exc
                logger.warning("Groq call attempt %d/%d failed: %s", attempt, retries + 1, exc)
                if attempt <= retries:
                    time.sleep(2 ** attempt)  # exponential backoff

        raise RuntimeError(f"Groq API call failed after {retries + 1} attempts: {last_error}")

    # ── JSON Parsing ──────────────────────────────────────────────

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM output with robust fallback extraction.

        Handles:
        - Clean JSON
        - JSON wrapped in ```json blocks
        - JSON with trailing commas
        - Partial JSON (extracts what it can)
        """
        raw = raw.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        # Try direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON object with regex
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning("Could not parse JSON from LLM output. Raw: %s...", raw[:200])
        return self._extract_fields_heuristic(raw)

    def _extract_fields_heuristic(self, text: str) -> Dict[str, Any]:
        """
        Last-resort: extract fields from unstructured LLM output using regex.
        """
        result: Dict[str, Any] = {}

        # risk_level
        rl_match = re.search(r'"risk_level"\s*:\s*"(\w+)"', text, re.IGNORECASE)
        if rl_match:
            result["risk_level"] = self._normalize_risk_level(rl_match.group(1))

        # risk_score
        rs_match = re.search(r'"risk_score"\s*:\s*(\d+)', text)
        if rs_match:
            result["risk_score"] = int(rs_match.group(1))

        # explanation
        expl_match = re.search(r'"explanation"\s*:\s*"([^"]+)"', text, re.DOTALL)
        if expl_match:
            result["explanation"] = expl_match.group(1)[:500]

        # suggested_alternative
        alt_match = re.search(r'"suggested_alternative"\s*:\s*"([^"]+)"', text, re.DOTALL)
        if alt_match:
            result["suggested_alternative"] = alt_match.group(1)[:1000]

        # risk_factors - try array
        rf_match = re.search(r'"risk_factors"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if rf_match:
            items = re.findall(r'"([^"]+)"', rf_match.group(1))
            result["risk_factors"] = items if items else ["Unable to parse risk factors."]

        # missing_protections - try array
        mp_match = re.search(r'"missing_protections"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        if mp_match:
            items = re.findall(r'"([^"]+)"', mp_match.group(1))
            result["missing_protections"] = items if items else []

        # Fill missing with defaults
        for key in ("risk_level", "risk_score", "risk_factors", "explanation", "suggested_alternative", "missing_protections"):
            if key not in result:
                result[key] = self._default_value(key)

        return result

    @staticmethod
    def _normalize_risk_level(value: Any) -> str:
        """Ensure risk_level is one of Low/Medium/High."""
        if isinstance(value, str):
            cleaned = value.strip().title()
            if cleaned in ("Low", "Medium", "High"):
                return cleaned
            if cleaned.startswith("High") or "high" in cleaned.lower():
                return "High"
            if cleaned.startswith("Med") or "medium" in cleaned.lower():
                return "Medium"
        return "Low"

    @staticmethod
    def _normalize_risk_score(value: Any) -> int:
        """Clamp risk_score to 0-100 integer."""
        try:
            score = int(float(str(value)))
            return max(0, min(100, score))
        except (ValueError, TypeError):
            return 50  # sensible default

    @staticmethod
    def _default_value(key: str) -> Any:
        """Return sensible defaults for missing JSON keys."""
        defaults: Dict[str, Any] = {
            "risk_level": "Low",
            "risk_score": 0,
            "risk_factors": [],
            "explanation": "",
            "suggested_alternative": "",
            "missing_protections": [],
        }
        return defaults.get(key, "")

    @staticmethod
    def _low_risk_result(message: str) -> Dict[str, Any]:
        """Return a pre-built low-risk result for empty/trivial clauses."""
        return {
            "risk_level": "Low",
            "risk_score": 0,
            "risk_factors": [],
            "explanation": message,
            "suggested_alternative": "",
            "missing_protections": [],
        }


# Module-level singleton
analyzer = ContractAnalyzer()
