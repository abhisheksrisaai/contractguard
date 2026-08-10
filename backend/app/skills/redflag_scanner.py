"""
ContractGuard - Red Flag Scanner
================================
Deterministic regex-based red flag detection across contract types.
"""

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# ── Universal patterns (all contract types) ─────────────────────────

UNIVERSAL_PATTERNS: List[Tuple[str, str, str, str]] = [
    # (regex, severity, category, description)
    (r"pay(?:ment)?[^.?!]{0,80}?when\s+(we\s+are\s+)?paid", "CRITICAL", "Payment",
     "Pay-when-paid — payment depends on receiving payment from a third party"),
    (r"payment\s+when\s+(we\s+are\s+)?paid", "CRITICAL", "Payment",
     "Pay-when-paid — payment depends on receiving payment from a third party"),
    (r"unlimited\s+liability", "CRITICAL", "Liability",
     "Unlimited liability — no cap on damages"),
    (r"without\s+any\s+limitation\s+of\s+liability", "CRITICAL", "Liability",
     "No limitation of liability — uncapped exposure"),
    (r"at\s+(our|the\s+supplier'?s?|the\s+employer'?s?)\s+sole\s+discretion", "HIGH", "Consent",
     "Sole discretion clause — one party can decide unilaterally"),
    (r"unilateral(?:ly)?\s+(?:amend|modify|change|terminate)", "CRITICAL", "Consent",
     "Unilateral amendment/termination — one-sided power to change terms"),
    (r"automatic(?:ally)?\s+renew", "HIGH", "Consent",
     "Automatic renewal — contract continues without explicit consent"),
    (r"reasonable\s+time", "HIGH", "Clarity",
     "Reasonable time — vague, unenforceable deadline"),
    (r"industry\s+standard", "HIGH", "Quality",
     "Industry standard — unmeasurable quality bar"),
    (r"perpetual", "MEDIUM", "Confidentiality",
     "Perpetual obligation — may be excessive"),
    (r"indemnify\s+and\s+hold\s+harmless", "HIGH", "Liability",
     "Broad indemnity — one-sided hold-harmless"),
    (r"in\s+no\s+event", "HIGH", "Liability",
     "Absolute disclaimer — attempts to disclaim all liability"),
]

SUPPLIER_PATTERNS: List[Tuple[str, str, str, str]] = [
    (r"risk\s+(?:shall\s+)?pass.*?dispatch", "MEDIUM", "Delivery",
     "Risk passes on dispatch — buyer bears transit risk"),
    (r"taxes\s+extra", "MEDIUM", "Taxation",
     "Taxes extra without rate — cost uncertainty"),
]

WORKS_PATTERNS: List[Tuple[str, str, str, str]] = [
    (r"to\s+(?:the\s+)?employer'?s?\s+satisfaction", "CRITICAL", "Quality",
     "To employer's satisfaction — no objective acceptance standard"),
    (r"as\s+directed\s+by\s+(?:the\s+)?(?:employer|engineer)", "HIGH", "Scope",
     "As directed by employer/engineer — unlimited scope expansion"),
    (r"time\s+is\s+of\s+the\s+essence", "MEDIUM", "Schedule",
     "Time is of the essence — strict deadline without EOT relief"),
]

# ── Missing clause checks per type ──────────────────────────────────

MISSING_CLAUSE_CHECKS: Dict[str, List[Tuple[str, str, str]]] = {
    "supplier_contract": [
        (r"\bforce\s+majeure\b", "HIGH", "No force majeure clause"),
        (r"\bgoverning\s+law\b|\bjurisdiction\b|\barbitration\b",
         "CRITICAL", "No dispute resolution clause"),
        (r"\bwarranty\b|\bwarrant\b", "HIGH", "No warranty clause"),
        (r"\bconfidential|NDA|non-disclosure\b",
         "MEDIUM", "No confidentiality clause"),
    ],
    "works_contract": [
        (r"\bdefect\s+liability\b", "HIGH", "No defect liability period"),
        (r"\bforce\s+majeure\b", "HIGH", "No force majeure clause"),
        (r"\bgoverning\s+law\b|\bjurisdiction\b|\barbitration\b",
         "CRITICAL", "No dispute resolution clause"),
        (r"\bperformance\s+security\b|\bperformance\s+bond\b",
         "HIGH", "No performance security clause"),
        (r"\binsurance\b", "HIGH", "No insurance clause"),
        (r"\bvariation\b|\bchange\s+order\b", "MEDIUM", "No variation procedure"),
    ],
    "employment_contract": [
        (r"\bgoverning\s+law\b|\bjurisdiction\b|\barbitration\b",
         "CRITICAL", "No dispute resolution clause"),
        (r"\bconfidential|NDA|non-disclosure\b",
         "MEDIUM", "No confidentiality clause"),
        (r"\bterminat(?:ion|e)\b", "HIGH", "No termination clause"),
    ],
    "partner_agreement": [
        (r"\bgoverning\s+law\b|\bjurisdiction\b|\barbitration\b",
         "CRITICAL", "No dispute resolution clause"),
        (r"\bterminat(?:ion|e)\b", "HIGH", "No termination clause"),
        (r"\bconfidential|NDA|non-disclosure\b",
         "MEDIUM", "No confidentiality clause"),
        (r"\bnon-compete\b|\bnon-solicit\b",
         "MEDIUM", "No non-compete/non-solicitation clause"),
    ],
    "service_agreement": [
        (r"\bgoverning\s+law\b|\bjurisdiction\b|\barbitration\b",
         "CRITICAL", "No dispute resolution clause"),
        (r"\bterminat(?:ion|e)\b", "HIGH", "No termination clause"),
        (r"\bconfidential|NDA|non-disclosure\b",
         "MEDIUM", "No confidentiality clause"),
    ],
    "nda": [
        (r"\bgoverning\s+law\b|\bjurisdiction\b|\barbitration\b",
         "CRITICAL", "No dispute resolution clause"),
    ],
    "purchase_order": [
        (r"\bgoverning\s+law\b|\bjurisdiction\b|\barbitration\b",
         "CRITICAL", "No dispute resolution clause"),
    ],
}


def scan_red_flags(contract_text: str, contract_type: str) -> List[dict]:
    """
    Scan contract text for red flags using deterministic regex patterns.

    Args:
        contract_text: Full contract text.
        contract_type: One of the 7 contract types (or 'unknown').

    Returns:
        List of dicts with keys: pattern, severity, category, evidence.
    """
    if not contract_text or not contract_text.strip():
        return []

    findings: List[dict] = []
    lower = contract_text.lower()
    seen: set = set()  # deduplicate by (pattern, severity)

    # ── Universal patterns ────────────────────────────────────────
    for pattern_str, severity, category, description in UNIVERSAL_PATTERNS:
        for m in re.finditer(pattern_str, lower, re.IGNORECASE):
            key = (pattern_str, severity)
            if key in seen:
                continue
            seen.add(key)

            # Extract evidence: the matched line + context
            pos = m.start()
            snippet = _extract_evidence(contract_text, pos, m.group())
            findings.append({
                "pattern": description,
                "severity": severity,
                "category": category,
                "evidence": snippet,
            })

    # ── Type-specific patterns ────────────────────────────────────
    type_patterns = SUPPLIER_PATTERNS if "supplier" in contract_type else (
        WORKS_PATTERNS if "works" in contract_type else []
    )
    for pattern_str, severity, category, description in type_patterns:
        for m in re.finditer(pattern_str, lower, re.IGNORECASE):
            key = (pattern_str, severity)
            if key in seen:
                continue
            seen.add(key)
            pos = m.start()
            snippet = _extract_evidence(contract_text, pos, m.group())
            findings.append({
                "pattern": description,
                "severity": severity,
                "category": category,
                "evidence": snippet,
            })

    # ── Missing clause detection ──────────────────────────────────
    checks = MISSING_CLAUSE_CHECKS.get(contract_type, [])
    for pattern_str, severity, description in checks:
        if not re.search(pattern_str, lower, re.IGNORECASE):
            key = (f"missing:{pattern_str}", severity)
            if key in seen:
                continue
            seen.add(key)
            findings.append({
                "pattern": f"MISSING: {description}",
                "severity": severity,
                "category": "Missing Clause",
                "evidence": "",
            })

    # Sort: CRITICAL first, then HIGH, MEDIUM
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda f: order.get(f["severity"], 99))

    logger.info(
        "Red flag scanner: %d findings for type=%s", len(findings), contract_type,
    )
    return findings


def _extract_evidence(text: str, pos: int, match: str) -> str:
    """Extract context around a match position (first 120 chars)."""
    start = max(0, pos - 10)
    end = min(len(text), pos + len(match) + 100)
    snippet = text[start:end].replace("\n", " ").strip()
    if len(snippet) > 120:
        snippet = snippet[:117] + "..."
    return snippet
