"""
ContractGuard - PDF Report Generator
====================================
Generates professional PDF reports from contract analysis results
using Jinja2 HTML templates and WeasyPrint (with fallback to HTML output).
"""

import logging
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

_WEASYPRINT_AVAILABLE: Optional[bool] = None


def _check_weasyprint() -> bool:
    global _WEASYPRINT_AVAILABLE
    if _WEASYPRINT_AVAILABLE is None:
        try:
            from weasyprint import HTML  # noqa: F401
            _WEASYPRINT_AVAILABLE = True
            logger.info("WeasyPrint PDF generation available.")
        except OSError as exc:
            logger.warning(
                "WeasyPrint unavailable (missing system libs): %s. "
                "Reports will be returned as HTML.", exc
            )
            _WEASYPRINT_AVAILABLE = False
    return _WEASYPRINT_AVAILABLE


def _safe_context(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build the template context with defensive defaults everywhere."""
    clauses = analysis_result.get("clauses", [])
    breakdown = analysis_result.get("breakdown", {"High": 0, "Medium": 0, "Low": 0})

    fair_matches = 0
    for clause in clauses:
        if clause.get("fair_alternatives") and len(clause.get("fair_alternatives", [])) > 0:
            fair_matches += 1

    overall = analysis_result.get("overall_score", 0)
    if overall >= 75:
        risk_class = "high"; risk_level = "High Risk"
    elif overall >= 45:
        risk_class = "medium"; risk_level = "Medium Risk"
    else:
        risk_class = "low"; risk_level = "Low Risk"

    findings = analysis_result.get("findings", []) or []
    f_critical = sum(1 for f in findings if f.get("severity") == "CRITICAL")
    f_high = sum(1 for f in findings if f.get("severity") == "HIGH")
    f_medium = sum(1 for f in findings if f.get("severity") == "MEDIUM")
    f_low = sum(1 for f in findings if f.get("severity") == "LOW")

    return {
        "report_id": str(uuid.uuid4())[:8],
        "generated_at": datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC"),
        "overall_score": int(overall),
        "risk_class": risk_class,
        "risk_level": risk_level,
        "assessment": analysis_result.get("assessment", ""),
        "breakdown": breakdown,
        "high_risk_count": breakdown.get("High", 0),
        "total_clauses": len(clauses),
        "fair_matches": fair_matches,
        "clauses": clauses,
        "contract_type": analysis_result.get("contract_type", ""),
        "confidence": analysis_result.get("confidence"),
        "recommended_action": analysis_result.get("recommended_action", ""),
        "five_c": analysis_result.get("five_c"),
        "red_flags": analysis_result.get("red_flags", []) or [],
        "executive_summary": analysis_result.get("executive_summary", ""),
        "findings": findings,
        "f_critical": f_critical,
        "f_high": f_high,
        "f_medium": f_medium,
        "f_low": f_low,
        "negotiation_opportunities": analysis_result.get("negotiation_opportunities", []) or [],
        "missing_clauses": analysis_result.get("missing_clauses", []) or [],
    }


class ReportGenerator:
    def __init__(self) -> None:
        self._templates_dir = Path(__file__).resolve().parent.parent / "templates"
        self._env: Optional[Environment] = None

    @property
    def env(self) -> Environment:
        if self._env is None:
            if not self._templates_dir.exists():
                raise FileNotFoundError(f"Templates directory not found: {self._templates_dir}")
            self._env = Environment(
                loader=FileSystemLoader(str(self._templates_dir)),
                autoescape=select_autoescape(["html", "xml"]),
            )
        return self._env

    def generate_report(self, analysis_result: Dict[str, Any]) -> bytes:
        logger.info("Generating PDF report...")

        context = _safe_context(analysis_result)

        # ── Render template (with one retry on stripped data) ──
        html_content = None
        try:
            template = self.env.get_template("report.html")
            html_content = template.render(**context)
        except Exception as exc:
            logger.warning(
                "Template render failed with full context (%s). Retrying with safe fallback.", exc
            )
            # Retry with stripped context (no five_c/red_flags/findings/negotiation)
            try:
                fallback_ctx = dict(context)
                fallback_ctx["five_c"] = None
                fallback_ctx["red_flags"] = []
                fallback_ctx["findings"] = []
                fallback_ctx["negotiation_opportunities"] = []
                fallback_ctx["missing_clauses"] = []
                fallback_ctx["recommended_action"] = ""
                html_content = template.render(**fallback_ctx)
                logger.info("Fallback template render succeeded.")
            except Exception as exc2:
                logger.error("Template rendering failed even with fallback: %s", exc2)
                raise RuntimeError(
                    f"Failed to render report template: {exc2}"
                ) from exc2

        # ── Convert to PDF (or HTML fallback) ──────────────────
        if _check_weasyprint():
            try:
                from weasyprint import HTML
                pdf_bytes = HTML(string=html_content).write_pdf()
                logger.info("PDF report generated successfully (%d bytes).", len(pdf_bytes))
                return pdf_bytes
            except Exception as exc:
                logger.error(
                    "WeasyPrint render failed (will return HTML): %s\n%s",
                    exc, traceback.format_exc(),
                )
                # Fall through to HTML return
        # Return HTML as fallback
        logger.info("Returning HTML report.")
        return html_content.encode("utf-8")

    def generate_simple_report(self, clauses: List[Dict[str, Any]]) -> bytes:
        breakdown = {"High": 0, "Medium": 0, "Low": 0}
        total_score = 0
        for c in clauses:
            level = c.get("risk_level", "Low")
            breakdown[level] = breakdown.get(level, 0) + 1
            total_score += c.get("risk_score", 0)

        overall = round(total_score / len(clauses)) if clauses else 0
        if overall >= 75:
            assessment = "High Risk — This contract requires significant attention before signing."
        elif overall >= 45:
            assessment = "Medium Risk — Several areas of concern. Negotiation recommended."
        else:
            assessment = "Low Risk — This contract appears generally balanced and fair."

        return self.generate_report({
            "clauses": clauses, "overall_score": overall,
            "breakdown": breakdown, "assessment": assessment,
            "total_clauses": len(clauses),
        })


report_generator = ReportGenerator()
