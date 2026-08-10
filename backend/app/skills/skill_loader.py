"""
ContractGuard - Skill Loader
============================
Reads backend/skills/<TypeDir>/Skill.md and returns parsed sections.
"""

import logging
import re
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ── Contract-type → skill directory mapping ─────────────────────────

CONTRACT_TYPE_SKILL_MAP: Dict[str, str] = {
    "employment_contract": "EmploymentContract",
    "supplier_contract":   "SupplierContract",
    "works_contract":      "WorksContract",
    "partner_agreement":   "PartnerAgreement",
    "service_agreement":   "SupplierContract",
    "nda":                 "SupplierContract",
    "purchase_order":      "SupplierContract",
    "unknown":             "EmploymentContract",
}


class SkillLoader:
    """
    Reads and caches Skill.md files from backend/skills/.
    """

    def __init__(self) -> None:
        self._skills_dir = (
            Path(__file__).resolve().parent.parent.parent / "skills"
        )
        self._cache: Dict[str, dict] = {}

    def _resolve_dir(self, contract_type: str) -> str:
        """Map contract type to skill directory name."""
        return CONTRACT_TYPE_SKILL_MAP.get(contract_type, "EmploymentContract")

    def load_skill(self, contract_type: str) -> dict:
        """
        Load and parse the Skill.md for the given contract type.

        Returns dict with keys: role, five_c_section, areas_section,
        red_flags_table, output_format_section.
        """
        skill_dir = self._resolve_dir(contract_type)

        if skill_dir in self._cache:
            return self._cache[skill_dir]

        skill_path = self._skills_dir / skill_dir / "Skill.md"
        if not skill_path.exists():
            logger.warning("Skill file not found: %s", skill_path)
            return self._empty_skill()

        content = skill_path.read_text(encoding="utf-8")
        parsed = self._parse_skill_md(content, skill_dir)
        self._cache[skill_dir] = parsed
        logger.info("Loaded skill '%s' (%d chars)", skill_dir, len(content))
        return parsed

    # ── Parsing ─────────────────────────────────────────────────────

    def _parse_skill_md(self, content: str, skill_dir: str) -> dict:
        """Parse a Skill.md into structured sections."""
        result = {
            "role": "",
            "five_c_section": "",
            "areas_section": "",
            "red_flags_table": "",
            "output_format_section": "",
            "skill_dir": skill_dir,
        }

        # Extract Role Definition fenced block
        role_match = re.search(
            r'##\s+Role\s+Definition\s*\n+```\s*\n(.*?)\n```',
            content, re.DOTALL | re.IGNORECASE,
        )
        if role_match:
            result["role"] = role_match.group(1).strip()

        # Extract 5C section (everything under "## Review Framework: 5 C" or
        # "## 5C" up to the next ## heading that is NOT a sub-heading)
        five_c = self._extract_section(
            content, r'##\s+(?:Review Framework:?\s*)?5\s*C', 2,
        )
        result["five_c_section"] = five_c[:3000] if five_c else ""

        # Extract Deep-Dive/Areas section
        areas = self._extract_section(
            content, r'##\s+Deep-Dive\s+Review\s+Areas', 2,
        )
        result["areas_section"] = areas[:4000] if areas else ""

        # Extract Autonomous Red Flag table
        red_flags = self._extract_section(
            content, r'##\s+Autonomous\s+(?:Risk\s+Detection|Red\s+Flag)', 2,
        )
        result["red_flags_table"] = red_flags[:2000] if red_flags else ""

        # Extract Output Format section
        out_fmt = self._extract_section(
            content, r'##\s+Output\s+Format', 2,
        )
        result["output_format_section"] = out_fmt[:2000] if out_fmt else ""

        return result

    @staticmethod
    def _extract_section(text: str, start_pattern: str, min_depth: int) -> str:
        """
        Extract a section from ##-style markdown.
        Finds text matching `start_pattern` and returns all content
        up to the next heading of equal or higher level.
        """
        m = re.search(start_pattern, text, re.IGNORECASE)
        if not m:
            return ""

        start = m.start()
        # Skip the heading line itself
        body_start = text.find("\n", m.end())
        if body_start == -1:
            body_start = len(text)

        # Find next ## heading (same level)
        rest = text[body_start:]
        next_heading = re.search(r'\n##\s+[^#]', rest)
        if next_heading:
            body = rest[:next_heading.start()]
        else:
            body = rest

        return body.strip()

    @staticmethod
    def _empty_skill() -> dict:
        return {
            "role": "",
            "five_c_section": "",
            "areas_section": "",
            "red_flags_table": "",
            "output_format_section": "",
            "skill_dir": "Unknown",
        }


skill_loader = SkillLoader()
