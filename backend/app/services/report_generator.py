"""
ContractGuard - PDF Report Generator

Generates professional PDF reports from contract analysis results
using Jinja2 HTML templates and WeasyPrint (with fallback to HTML output).
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy-check if WeasyPrint is fully available (needs system libs: pango, gdk-pixbuf)
_WEASYPRINT_AVAILABLE: Optional[bool] = None


def _check_weasyprint() -> bool:
    """Check if WeasyPrint PDF generation is available."""
    global _WEASYPRINT_AVAILABLE
    if _WEASYPRINT_AVAILABLE is None:
        try:
            from weasyprint import HTML  # noqa: F401
            _WEASYPRINT_AVAILABLE = True
            logger.info("WeasyPrint PDF generation available.")
        except OSError as exc:
            logger.warning(
                "WeasyPrint unavailable (missing system libs): %s. "
                "Reports will be returned as HTML. "
                "Install: brew install pango gdk-pixbuf libffi",
                exc,
            )
            _WEASYPRINT_AVAILABLE = False
    return _WEASYPRINT_AVAILABLE


class ReportGenerator:
    """
    Generates a styled PDF report from contract analysis data.

    Uses:
    - Jinja2 for HTML templating
    - WeasyPrint for HTML → PDF conversion
    """

    def __init__(self) -> None:
        self._templates_dir = Path(__file__).resolve().parent.parent / "templates"
        self._env: Optional[Environment] = None

    @property
    def env(self) -> Environment:
        """Lazy-initialize Jinja2 environment."""
        if self._env is None:
            if not self._templates_dir.exists():
                raise FileNotFoundError(
                    f"Templates directory not found: {self._templates_dir}"
                )
            self._env = Environment(
                loader=FileSystemLoader(str(self._templates_dir)),
                autoescape=select_autoescape(["html", "xml"]),
            )
        return self._env

    def generate_report(self, analysis_result: Dict[str, Any]) -> bytes:
        """
        Generate a PDF report from contract analysis results.

        Args:
            analysis_result: Dict with keys:
                - overall_score, risk_level, assessment
                - breakdown (High/Medium/Low counts)
                - clauses (list of analyzed clause dicts)
                - total_clauses, etc.

        Returns:
            PDF file bytes.
        """
        logger.info("Generating PDF report...")

        report_id = str(uuid.uuid4())[:8]

        # ── Prepare template context ──────────────────────────
        clauses = analysis_result.get("clauses", [])
        breakdown = analysis_result.get("breakdown", {"High": 0, "Medium": 0, "Low": 0})

        # Count fair alternatives matched
        fair_matches = 0
        for clause in clauses:
            if clause.get("fair_alternatives") and len(clause.get("fair_alternatives", [])) > 0:
                fair_matches += 1

        # Determine risk class
        overall = analysis_result.get("overall_score", 0)
        if overall >= 70:
            risk_class = "high"
            risk_level = "High Risk"
        elif overall >= 40:
            risk_class = "medium"
            risk_level = "Medium Risk"
        else:
            risk_class = "low"
            risk_level = "Low Risk"

        context = {
            "report_id": report_id,
            "generated_at": datetime.now().strftime("%B %d, %Y at %H:%M UTC"),
            "overall_score": int(overall),
            "risk_class": risk_class,
            "risk_level": risk_level,
            "assessment": analysis_result.get("assessment", "No assessment available."),
            "breakdown": breakdown,
            "high_risk_count": breakdown.get("High", 0),
            "total_clauses": len(clauses),
            "fair_matches": fair_matches,
            "clauses": clauses,
        }

        # ── Render HTML ───────────────────────────────────────
        try:
            template = self.env.get_template("report.html")
            html_content = template.render(**context)
        except Exception as exc:
            logger.error("Template rendering failed: %s", exc)
            raise RuntimeError(f"Failed to render report template: {exc}") from exc

        # ── Convert to PDF (or fall back to HTML) ─────────────
        if _check_weasyprint():
            try:
                from weasyprint import HTML
                pdf_bytes = HTML(string=html_content).write_pdf()
                logger.info("PDF report generated successfully (%d bytes).", len(pdf_bytes))
                return pdf_bytes
            except Exception as exc:
                logger.error("WeasyPrint PDF generation failed: %s", exc)
                raise RuntimeError(f"Failed to generate PDF: {exc}") from exc
        else:
            # Return HTML as fallback (wrapped in a PDF-like response)
            logger.info("Returning HTML report (WeasyPrint unavailable).")
            return html_content.encode("utf-8")

    def generate_simple_report(self, clauses: List[Dict[str, Any]]) -> bytes:
        """
        Convenience method: generate a report directly from raw clauses
        (does light aggregation first).

        Args:
            clauses: List of analyzed clause dicts.

        Returns:
            PDF bytes.
        """
        # Compute simple aggregation
        breakdown = {"High": 0, "Medium": 0, "Low": 0}
        total_score = 0
        for c in clauses:
            level = c.get("risk_level", "Low")
            breakdown[level] = breakdown.get(level, 0) + 1
            total_score += c.get("risk_score", 0)

        overall = round(total_score / len(clauses)) if clauses else 0
        if overall >= 70:
            assessment = "High Risk — This contract requires significant attention before signing."
        elif overall >= 40:
            assessment = "Medium Risk — Several areas of concern. Negotiation recommended."
        else:
            assessment = "Low Risk — This contract appears generally balanced and fair."

        analysis = {
            "clauses": clauses,
            "overall_score": overall,
            "breakdown": breakdown,
            "assessment": assessment,
            "total_clauses": len(clauses),
        }
        return self.generate_report(analysis)


# Module-level singleton
report_generator = ReportGenerator()
