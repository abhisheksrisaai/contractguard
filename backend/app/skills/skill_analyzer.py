"""
ContractGuard - Skill Analyzer
==============================
Coordinates LLM-powered skill analysis with exactly 2 Groq calls.
"""

import logging
from typing import Any, Dict, List, Optional

from app.services.llm_service import ContractAnalyzer, SYSTEM_PROMPT as _BASE_SYSTEM
from app.skills.skill_loader import skill_loader
from app.skills.redflag_scanner import scan_red_flags

logger = logging.getLogger(__name__)


class SkillAnalyzer:
    """
    Runs a structured skill-based contract analysis using the skill
    definition (Skill.md) for guidance. Uses EXACTLY 2 Groq LLM calls.
    """

    def __init__(self, llm: ContractAnalyzer, rag: Any) -> None:
        self.llm = llm
        self.rag = rag

    def analyze(
        self,
        contract_text: str,
        contract_type: str,
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

        # Trim contract text (LLM has token limits)
        trimmed = contract_text[:12000]

        # ── CALL 1: 5Cs + summary ─────────────────────────────────
        call1_ok = False
        five_c = self._default_five_c()
        executive_summary = ""
        missing_clauses: List[str] = []
        recommended_action = "PROCEED WITH CAUTION"
        confidence = 60

        try:
            result1 = self._call_5c_and_summary(
                role, five_c_template, trimmed,
            )
            if result1:
                five_c = result1.get("five_c", five_c)
                executive_summary = result1.get("executive_summary", "")
                missing_clauses = result1.get("missing_clauses", [])
                recommended_action = result1.get("recommended_action", "PROCEED WITH CAUTION")
                confidence = result1.get("confidence", 60)
                call1_ok = True
        except Exception as exc:
            logger.warning("5C + summary call failed: %s", exc)
            confidence -= 10

        # ── CALL 2: Detailed findings ─────────────────────────────
        call2_ok = False
        llm_findings: List[dict] = []

        try:
            result2 = self._call_area_findings(role, areas_checklist, trimmed)
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
            "Skill analysis: type=%s, 5C=%s, findings=%d, confidence=%d",
            contract_type, call1_ok, len(llm_findings), confidence,
        )

        return {
            "five_c": five_c,
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
            + trimmed_text[:10000]
            + "\n\nJSON with keys: five_c (object with capacity/consent/"
            "consideration/clarity/compliance — each has status Pass|Partial|Fail, "
            "score 0-100, issues array), executive_summary (3-4 sentences), "
            "missing_clauses (array of strings), recommended_action "
            "(PROCEED|PROCEED WITH CAUTION|RENEGOTIATE|DO NOT SIGN), "
            "confidence (0-100). Only JSON, no commentary."
        )

        raw = self.llm._call_groq(system, user, temperature=0.2, max_tokens=1024)
        return self.llm._parse_json(raw)

    def _call_area_findings(
        self, role: str, areas_checklist: str, trimmed_text: str,
    ) -> Optional[List[dict]]:
        """CALL 2: Identify 8-12 risk findings across review areas."""
        system = (
            (role or "You are an expert contract reviewer.") + "\n\n"
            + "Identify the 8-12 most important risk findings across "
            "the review areas. Return ONLY a JSON array.\n\n"
            + (areas_checklist or "")[:4000]
        )
        user = (
            "Contract text:\n\n" + trimmed_text[:10000]
            + "\n\nReturn a JSON array of 8-12 findings. Each finding: "
            '{"area": "...", "severity": "CRITICAL|HIGH|MEDIUM|LOW", '
            '"finding": "...", "clause_reference": "...", '
            '"why_it_matters": "...", "industry_best_practice": "...", '
            '"suggested_negotiation": "...", "suggested_clause": "...", '
            '"priority": "High|Medium|Low"}. Only JSON, no commentary.'
        )

        raw = self.llm._call_groq(system, user, temperature=0.3, max_tokens=1500)
        parsed = self.llm._parse_json(raw)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "findings" in parsed:
            return parsed["findings"]
        return None

    @staticmethod
    def _default_five_c() -> dict:
        return {
            "capacity":      {"status": "Partial", "score": 50, "issues": ["Unable to verify automatically"]},
            "consent":       {"status": "Partial", "score": 50, "issues": ["Unable to verify automatically"]},
            "consideration": {"status": "Partial", "score": 50, "issues": ["Unable to verify automatically"]},
            "clarity":       {"status": "Partial", "score": 50, "issues": ["Unable to verify automatically"]},
            "compliance":    {"status": "Partial", "score": 50, "issues": ["Unable to verify automatically"]},
        }
