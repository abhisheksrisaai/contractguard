"""
ContractGuard - Day 8c Tests
Verify contract classifier, red-flag scanner, skill loader, and skill analyzer.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.contract_classifier import ContractTypeClassifier
from app.skills.redflag_scanner import scan_red_flags
from app.skills.skill_loader import SkillLoader
from app.skills.skill_analyzer import SkillAnalyzer
from app.services.llm_service import ContractAnalyzer
from app.services.rag_service import rag_service


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def classifier():
    return ContractTypeClassifier()

@pytest.fixture(scope="module")
def loader():
    return SkillLoader()

@pytest.fixture(scope="module")
def analyzer():
    llm = ContractAnalyzer()
    return SkillAnalyzer(llm, rag_service)


# ── Classifier: employment → employment_contract ────────────────────

def test_classify_employment_contract(classifier):
    text = """
    EMPLOYMENT AGREEMENT
    
    This Employment Agreement is entered into between ABC Corp (Employer)
    and John Doe (Employee). The Employee shall receive a monthly salary
    of Rs. 50,000. The notice period shall be 30 days. The Employee is
    entitled to gratuity as per the Payment of Gratuity Act, 1972.
    Probation period is 6 months. The Employee shall work 48 hours per
    week with overtime at 2x rate.
    """
    ctype, confidence = classifier.classify(text)
    assert ctype == "employment_contract", f"Expected employment_contract, got {ctype}"
    assert confidence > 0.5, f"Confidence {confidence} too low"


# ── Classifier: works-flavored → works_contract ────────────────────

def test_classify_works_contract(classifier):
    text = """
    WORKS CONTRACT AGREEMENT
    
    This Works Contract is between Employer and Contractor for the
    construction of a commercial building. The BOQ (Bill of Quantities)
    is attached as Annexure A. The Defect Liability Period is 12 months
    from Practical Completion. EOT shall be granted for force majeure.
    Variation Orders require mutual agreement. Performance Security is
    10% of contract value. Retention money is 5% until DLP end.
    """
    ctype, confidence = classifier.classify(text)
    assert ctype == "works_contract", f"Expected works_contract, got {ctype}"
    assert confidence > 0.5, f"Confidence {confidence} too low"


# ── Classifier: gibberish → unknown ─────────────────────────────────

def test_classify_unknown_gibberish(classifier):
    text = "blah blah something something nothing relevant here"
    ctype, confidence = classifier.classify(text)
    # Should be unknown (no keywords match) or a type with confidence 0
    if ctype == "unknown":
        assert confidence == 0.0
    # Otherwise: very low confidence
    assert confidence < 0.6


# ── Classifier: empty text → unknown ────────────────────────────────

def test_classify_empty_text(classifier):
    ctype, confidence = classifier.classify("")
    assert ctype == "unknown"
    assert confidence == 0.0

    ctype2, confidence2 = classifier.classify("   ")
    assert ctype2 == "unknown"
    assert confidence2 == 0.0


# ── Red Flag Scanner: pay-when-paid → CRITICAL ──────────────────────

def test_redflag_pay_when_paid():
    text = "Payment shall be made to the Supplier only when we are paid by our client."
    findings = scan_red_flags(text, "supplier_contract")
    pay_when = [f for f in findings if "pay-when-paid" in f["pattern"].lower() or "pay when" in f["pattern"].lower()]
    assert len(pay_when) >= 1, f"No pay-when-paid finding. Got: {[f['pattern'] for f in findings]}"
    assert pay_when[0]["severity"] == "CRITICAL"
    assert len(pay_when[0]["evidence"]) > 0


# ── Red Flag Scanner: missing governing law → CRITICAL ──────────────

def test_redflag_missing_governing_law():
    text = "The Supplier agrees to provide goods as per this agreement. Payment within 30 days. Delivery to site. No liability for delays."
    findings = scan_red_flags(text, "works_contract")
    missing = [f for f in findings if "MISSING" in f["pattern"]]
    # Should include missing dispute resolution
    dispute = [f for f in missing if "dispute" in f["pattern"].lower() or "governing" in f["pattern"].lower()]
    assert len(dispute) >= 1, f"No missing dispute finding. Missing: {[f['pattern'] for f in missing]}"
    assert dispute[0]["severity"] == "CRITICAL"


# ── Red Flag Scanner: empty text → no findings ─────────────────────

def test_redflag_empty_text():
    findings = scan_red_flags("", "employment_contract")
    assert findings == []
    findings2 = scan_red_flags("   ", "employment_contract")
    assert findings2 == []


# ── Skill Loader: loads SupplierContract skill ──────────────────────

def test_skill_loader_supplier_contract(loader):
    skill = loader.load_skill("supplier_contract")
    assert len(skill["role"]) > 100, f"Role too short: {len(skill['role'])} chars"
    assert len(skill["five_c_section"]) > 100, f"5C section too short"
    assert len(skill["areas_section"]) > 100, f"Areas section too short"
    assert "capacity" in skill["five_c_section"].lower()

    # Test cache
    skill2 = loader.load_skill("supplier_contract")
    assert skill is skill2 or skill == skill2  # should be cached


# ── Skill Loader: maps service_agreement to SupplierContract ────────

def test_skill_loader_service_falls_back_to_supplier(loader):
    skill = loader.load_skill("service_agreement")
    assert len(skill["role"]) > 100
    assert skill.get("skill_dir") == "SupplierContract"


# ── Skill Loader: unknown → EmploymentContract ──────────────────────

def test_skill_loader_unknown_falls_back(loader):
    skill = loader.load_skill("unknown")
    assert skill.get("skill_dir") == "EmploymentContract"
    assert len(skill["role"]) > 50


# ── Skill Analyzer: partial results on all inputs ────────────────────

def test_skill_analyzer_returns_required_keys(analyzer):
    """Even with no Groq connectivity, analyze() must return all required
    keys without raising an exception."""
    contract_text = (
        "EMPLOYMENT AGREEMENT\n\n"
        "Employee: John Doe\n"
        "Employer: ABC Corp\n"
        "Salary: Rs. 50,000 per month\n"
        "Notice Period: 30 days\n"
    )

    result = analyzer.analyze(contract_text, "employment_contract")

    required_keys = [
        "five_c", "executive_summary", "missing_clauses",
        "findings", "negotiation_opportunities",
        "recommended_action", "confidence",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"

    # five_c must have all 5 C's even if default
    for c in ("capacity", "consent", "consideration", "clarity", "compliance"):
        assert c in result["five_c"], f"Missing five_c.{c}"

    assert isinstance(result["findings"], list)
    assert isinstance(result["missing_clauses"], list)
    assert isinstance(result["negotiation_opportunities"], list)
    assert 0 <= result["confidence"] <= 100

    # recommended_action must be one of the valid actions
    assert result["recommended_action"] in (
        "PROCEED", "PROCEED WITH CAUTION", "RENEGOTIATE", "DO NOT SIGN",
    )


# ── Skill Analyzer: unknown type still works ────────────────────────

def test_skill_analyzer_unknown_type(analyzer):
    result = analyzer.analyze("Some contract text.", "unknown")
    assert "five_c" in result
    assert result["confidence"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
