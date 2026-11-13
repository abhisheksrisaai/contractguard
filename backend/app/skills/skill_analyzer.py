"""
ContractGuard - Skill Analyzer
==============================
Coordinates LLM-powered skill analysis with exactly 2 provider calls.
"""

import logging
from typing import Any, Dict, List, Optional

from app.core.status import FiveCStatus
from app.services.llm_service import ContractAnalyzer, SYSTEM_PROMPT as _BASE_SYSTEM
from app.skills.skill_loader import skill_loader
from app.skills.redflag_scanner import scan_red_flags

logger = logging.getLogger(__name__)


class SkillAnalyzer:
    """
    Runs a structured skill-based contract analysis using the skill
    definition (Skill.md) for guidance. Uses EXACTLY 2 LLM calls.
    """

    def __init__(self, llm: ContractAnalyzer, rag: Any) -> None:
        self.llm = llm
        self.rag = rag

    def analyze(
        self,
        contract_text: str,
        contract_type: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the full skill-based analysis pipeline.

        Args:
            contract_text: Full contract text.
            contract_type: One of the 7 types (or 'unknown').

        Returns:
            Dict with keys: five_c, executive_summary, missing_clauses,
            findings, negotiation_opportunities, recommended_action, confidence.
        """
        skill = skill_loader.load_skill(contract_type)
        role = skill.get("role", "")
        five_c_template = skill.get("five_c_section", "")
        areas_checklist = skill.get("areas_section", "")

        # Trim contract text (token budget)
        trimmed = contract_text[:9000]

        # ── CALL 1: 5Cs + summary ─────────────────────────────────
        call1_ok = False
        five_c = self._unavailable_five_c()
        five_c_status = FiveCStatus.UNAVAILABLE.value
        executive_summary = ""
        missing_clauses: List[str] = []
        recommended_action = "PROCEED WITH CAUTION"
        confidence = 60

        try:
            result1 = self._call_5c_and_summary(
                role, five_c_template, trimmed, model,
            )
            if result1:
                five_c = result1["five_c"]
                five_c_status = self._five_c_state(five_c)
                executive_summary = result1.get("executive_summary", "")
                missing_clauses = result1.get("missing_clauses", [])
                recommended_action = result1.get("recommended_action", "PROCEED WITH CAUTION")
                confidence = result1.get("confidence", 60)
                call1_ok = True
        except Exception as exc:
            logger.warning("5C + summary call failed: %s", exc)
            # One compact retry. The first call can fail when the clause
            # workers have just consumed the lane's token budget; a shorter
            # prompt usually gets through without fabricating five 50s.
            try:
                result1 = self._call_5c_and_summary(
                    role, five_c_template, trimmed[:4500], model,
                    require_all=False,
                )
                if result1:
                    five_c = result1["five_c"]
                    five_c_status = self._five_c_state(five_c)
                    executive_summary = result1.get("executive_summary", "")
                    missing_clauses = result1.get("missing_clauses", [])
                    recommended_action = result1.get("recommended_action", "PROCEED WITH CAUTION")
                    confidence = result1.get("confidence", 60)
                    call1_ok = True
                    if five_c_status == FiveCStatus.PARTIAL.value:
                        confidence -= 5
            except Exception as retry_exc:
                logger.warning("5C + summary retry failed: %s", retry_exc)
                confidence -= 10

        # ── CALL 2: Detailed findings ─────────────────────────────
        call2_ok = False
        llm_findings: List[dict] = []

        try:
            result2 = self._call_area_findings(role, areas_checklist, trimmed, model)
            if result2:
                llm_findings = result2
                call2_ok = True
        except Exception as exc:
            logger.warning("Area findings call failed: %s", exc)
            confidence -= 10

        # ── Merge with red-flag scanner results ────────────────────
        scanner_findings = scan_red_flags(contract_text, contract_type)

        # Build a set of existing finding descriptions (case-insensitive)
        existing_texts = {
            f.get("finding", "").lower() for f in llm_findings
        }
        for sf in scanner_findings:
            if sf["pattern"].lower() not in existing_texts:
                llm_findings.append({
                    "area": "Auto-Detected",
                    "severity": sf["severity"],
                    "finding": sf["pattern"],
                    "clause_reference": "",
                    "why_it_matters": sf.get("evidence", ""),
                    "industry_best_practice": "",
                    "suggested_negotiation": "",
                    "suggested_clause": "",
                    "priority": {
                        "CRITICAL": "High", "HIGH": "High",
                        "MEDIUM": "Medium", "LOW": "Low",
                    }.get(sf["severity"], "Medium"),
                })

        # Merge missing clauses from scanner
        scanner_missing = [
            sf["pattern"].replace("MISSING: ", "")
            for sf in scanner_findings
            if sf["category"] == "Missing Clause"
        ]
        for sm in scanner_missing:
            if sm.lower() not in {m.lower() for m in missing_clauses}:
                missing_clauses.append(sm)

        # ── Build negotiation opportunities ────────────────────────
        negotiation_opportunities: List[dict] = []
        for f in llm_findings:
            if f.get("severity", "") in ("CRITICAL", "HIGH", "MEDIUM"):
                negotiation_opportunities.append({
                    "risk": f.get("finding", ""),
                    "why_it_matters": f.get("why_it_matters", ""),
                    "industry_best_practice": f.get("industry_best_practice", ""),
                    "suggested_negotiation": f.get("suggested_negotiation", ""),
                    "suggested_clause": f.get("suggested_clause", ""),
                    "priority": f.get("priority", "Medium"),
                })

        # ── Confidence penalties ───────────────────────────────────
        if len(llm_findings) == 0:
            confidence -= 15
        confidence = max(40, min(98, confidence))
        if not call1_ok and not call2_ok:
            confidence = 40

        logger.info(
            "Skill analysis: type=%s, 5C=%s, five_c_status=%s, findings=%d, confidence=%d",
            contract_type, call1_ok, five_c_status, len(llm_findings), confidence,
        )

        return {
            "five_c": five_c,
            "five_c_status": five_c_status,
            "executive_summary": executive_summary,
            "missing_clauses": missing_clauses,
            "findings": llm_findings,
            "negotiation_opportunities": negotiation_opportunities,
            "recommended_action": recommended_action,
            "confidence": confidence,
        }

    # ── LLM Calls ──────────────────────────────────────────────────

    def _call_5c_and_summary(
        self, role: str, five_c_template: str, trimmed_text: str,
        model: Optional[str] = None, require_all: bool = True,
    ) -> Optional[dict]:
        """CALL 1: Validate 5Cs and produce executive summary."""
        system = (
            (role or "You are an expert contract reviewer.") + "\n\n"
            + "You validate the 5 Cs of contract enforceability: "
            "Capacity, Consent, Consideration, Clarity, Compliance.\n\n"
            + (five_c_template or "")[:3000]
        )
        user = (
            "Analyze this contract and respond with ONLY valid JSON:\n\n"
            + trimmed_text[:8000]
            + "\n\nJSON with keys: five_c (object with capacity/consent/"
            "consideration/clarity/compliance — each has status Pass|Partial|Fail, "
            "score 0-100, issues array of one or two short strings), "
            "executive_summary (3-4 sentences), missing_clauses (array of strings), "
            "recommended_action (PROCEED|PROCEED WITH CAUTION|RENEGOTIATE|DO NOT SIGN), "
            "confidence (0-100). Only JSON, no commentary."
        )

        raw = self.llm._call_llm(system, user, temperature=0.2, max_tokens=1000, model=model)
        parsed = self.llm._parse_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError("5C response was not a JSON object.")
        parsed["five_c"] = self._normalize_five_c(
            parsed.get("five_c")
            or parsed.get("five_cs")
            or parsed.get("fiveCs")
            or {key: parsed.get(key) for key in (
                "capacity", "consent", "consideration", "clarity", "compliance",
            ) if isinstance(parsed.get(key), dict)},
            require_all=require_all,
        )
        return parsed

    @staticmethod
    def _five_c_state(five_c: Dict[str, Any]) -> str:
        scores = [data.get("score") for data in five_c.values()]
        if any(score is not None for score in scores):
            return (
                FiveCStatus.COMPLETE.value
                if all(score is not None for score in scores)
                else FiveCStatus.PARTIAL.value
            )
        return FiveCStatus.UNAVAILABLE.value

    @staticmethod
    def _normalize_five_c(five_c: Any, require_all: bool = True) -> Dict[str, Any]:
        """Validate and normalize the five-C shape.

        With ``require_all`` the call raises when any of the five checks is
        missing, which triggers one retry. A relaxed retry keeps whichever
        checks the model did return and marks the rest Unavailable instead of
        throwing away valid partial output or inventing scores.
        """
        if not isinstance(five_c, dict):
            raise ValueError("5C response was missing the five_c object.")

        # Smaller fallback models sometimes title-case the keys.
        lowered = {
            str(key).strip().lower().replace(" ", "_"): value
            for key, value in five_c.items()
        }

        normalized: Dict[str, Any] = {}
        missing: List[str] = []
        for key in ("capacity", "consent", "consideration", "clarity", "compliance"):
            data = lowered.get(key)
            if not isinstance(data, dict):
                missing.append(key)
                normalized[key] = {
                    "status": "Unavailable",
                    "score": None,
                    "issues": ["This check was not returned by the model."],
                }
                continue
            score = data.get("score")
            if isinstance(score, str) and score.strip().isdigit():
                score = int(score.strip())
            if not isinstance(score, (int, float)):
                missing.append(key)
                normalized[key] = {
                    "status": "Unavailable",
                    "score": None,
                    "issues": ["The model returned no numeric score for this check."],
                }
                continue
            status = str(data.get("status") or "Partial").strip().title()
            if status not in ("Pass", "Partial", "Fail"):
                status = "Partial"
            issues = data.get("issues")
            if not isinstance(issues, list):
                issues = [str(issues)] if issues else []
            normalized[key] = {
                "status": status,
                "score": max(0, min(100, int(round(score)))),
                "issues": [str(issue) for issue in issues if str(issue).strip()],
            }

        if require_all and missing:
            raise ValueError(
                "5C response was missing " + ", ".join(missing) + "."
            )
        return normalized

    @staticmethod
    def _unavailable_five_c() -> dict:
        """Explicit, honest state when the 5C call cannot complete.

        Never return five invented 50/100 scores: that looks like a real
        result and hides the failure from the user.
        """
        return {
            key: {
                "status": "Unavailable",
                "score": None,
                "issues": ["The 5C check could not be completed on this run."],
            }
            for key in (
                "capacity", "consent", "consideration", "clarity", "compliance",
            )
        }

    # Backward-compatible alias for older callers/tests.
    _default_five_c = _unavailable_five_c

    def _call_area_findings(
        self, role: str, areas_checklist: str, trimmed_text: str,
        model: Optional[str] = None,
    ) -> Optional[List[dict]]:
        """CALL 2: Identify the most important risk findings across review areas."""
        system = (
            (role or "You are an expert contract reviewer.") + "\n\n"
            + "Identify the 5 most important risk findings across "
            "the review areas. Return ONLY a JSON array.\n\n"
            + (areas_checklist or "")[:4000]
        )
        user = (
            "Contract text:\n\n" + trimmed_text[:8000]
            + "\n\nReturn a JSON array of 5 findings. Keep every field to one "
            "short sentence; suggested_clause must be at most 25 words. Each finding: "
            '{"area": "...", "severity": "CRITICAL|HIGH|MEDIUM|LOW", '
            '"finding": "...", "clause_reference": "...", '
            '"why_it_matters": "...", "industry_best_practice": "...", '
            '"suggested_negotiation": "...", "suggested_clause": "...", '
            '"priority": "High|Medium|Low"}. Only JSON, no commentary.'
        )

        # Qwen's free tier enforces a 1,000 output-token-per-minute cap. A
        # larger max_tokens is rejected before the model runs.
        raw = self.llm._call_llm(system, user, temperature=0.3, max_tokens=1000, model=model)
        parsed = self.llm._parse_json_list(raw)
        if isinstance(parsed, list):
            return parsed[:5]
        if isinstance(parsed, dict) and "findings" in parsed:
            return parsed["findings"][:5]
        return None
