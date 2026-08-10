"""
ContractGuard - Contract Type Classifier
========================================
Classifies contracts into one of 7 types using keyword/phrase scoring
with optional cheap LLM fallback for low-confidence cases.
"""

import logging
import re
from typing import Dict, List, Tuple, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Keyword definitions per contract type ───────────────────────────

TYPE_KEYWORDS: Dict[str, List[str]] = {
    "employment_contract": [
        "employee", "employer", "employment", "salary", "notice period",
        "gratuity", "probation", "appointment letter", "termination of employment",
        "working hours", "leave policy", "provident fund", "esi",
        "industrial employment", "standing orders", "wages", "pay slip",
        "confirmation", "permanent", "temporary employee", "fixed-term employee",
    ],
    "supplier_contract": [
        "supplier", "vendor", "purchase order", "supply of goods",
        "incoterms", "delivery schedule", "unit rate", "gstin of supplier",
        "supply agreement", "trade terms", "logistics", "freight",
        "packing", "shipping", "consignment", "warehouse",
        "inventory", "lead time", "purchase requisition",
    ],
    "works_contract": [
        "works contract", "contractor", "employer", "boq",
        "bill of quantities", "practical completion", "defect liability period",
        "eot", "variation order", "milestone", "mobilization advance",
        "retention money", "performance security", "construction", "civil works",
        "mep", "turnkey", "epc", "fidic", "completion certificate",
        "temporary works", "site", "drawings", "specifications",
        "engineer", "quantity surveyor", "delay damages",
    ],
    "partner_agreement": [
        "partner agreement", "channel partner", "full service partner",
        "fsp", "revenue share", "commission", "referral", "territory",
        "partnership", "alliance", "collaboration", "joint venture",
        "distribution", "reseller", "franchise", "license",
        "exclusivity", "non-compete", "customer base", "market",
    ],
    "service_agreement": [
        "services agreement", "statement of work", "sow", "consultant",
        "deliverables", "service levels", "sla", "professional services",
        "managed services", "support services", "maintenance",
        "scope of work", "work product", "time and materials",
        "fixed price", "milestone", "acceptance criteria", "warranty",
    ],
    "nda": [
        "non-disclosure", "receiving party", "disclosing party",
        "confidential information", "nda", "confidentiality agreement",
        "trade secret", "proprietary", "non-disclosure agreement",
        "confidentiality undertaking", "secrecy", "non-circumvention",
    ],
    "purchase_order": [
        "purchase order", "po number", "ship to", "bill to",
        "order confirmation", "procurement", "requisition",
        "material receipt", "goods receipt", "invoice",
        "payment terms", "delivery date", "item code",
    ],
}


class ContractTypeClassifier:
    """
    Classifies a contract into one of 7 types via keyword scoring,
    with an optional cheap LLM fallback for low-confidence cases.
    """

    def classify(self, contract_text: str) -> Tuple[str, float]:
        """
        Classify contract text.

        Args:
            contract_text: Full raw contract text.

        Returns:
            Tuple of (contract_type, confidence) where confidence is 0.0-1.0.
        """
        if not contract_text or not contract_text.strip():
            return ("unknown", 0.0)

        lower = contract_text.lower()

        scores: Dict[str, int] = {}
        for ctype, keywords in TYPE_KEYWORDS.items():
            score = 0
            for kw in keywords:
                count = len(re.findall(re.escape(kw), lower))
                score += count
            if score > 0:
                scores[ctype] = score

        if not scores:
            return ("unknown", 0.0)

        best_type = max(scores, key=lambda k: scores[k])  # type: ignore[arg-type]
        total = sum(scores.values())
        confidence = scores[best_type] / total if total > 0 else 0.0

        logger.info(
            "Classifier: best=%s, confidence=%.3f, top3=%s",
            best_type, confidence,
            {k: v for k, v in sorted(scores.items(), key=lambda x: -x[1])[:3]},
        )

        if confidence < 0.35:
            logger.info("Low confidence (%.3f). Attempting LLM fallback.", confidence)
            llm_type = self._llm_fallback(contract_text)
            if llm_type and llm_type != "unknown":
                logger.info("LLM fallback returned: %s", llm_type)
                return (llm_type, 0.5)

        return (best_type, confidence)

    def _llm_fallback(self, contract_text: str) -> Optional[str]:
        """Cheap LLM classification using llama-3.1-8b-instant."""
        try:
            from groq import Groq
            settings.validate_groq_key()
            client = Groq(api_key=settings.GROQ_API_KEY)

            system = (
                "Classify the contract type. Reply with exactly one of: "
                "employment_contract, supplier_contract, works_contract, "
                "partner_agreement, service_agreement, nda, purchase_order, "
                "unknown. No commentary, no punctuation."
            )
            user = contract_text[:2000]

            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
                max_tokens=10,
            )
            content = completion.choices[0].message.content
            if content:
                result = content.strip().lower().rstrip(".")
                valid = set(TYPE_KEYWORDS.keys()) | {"unknown"}
                if result in valid:
                    return result
            return None

        except Exception as exc:
            logger.warning("LLM fallback failed: %s", exc)
            return None


contract_classifier = ContractTypeClassifier()
