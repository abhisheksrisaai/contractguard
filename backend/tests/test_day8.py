"""
ContractGuard - Day 8 Tests
Verify improved clause segmentation: decimal numbering, lettered items,
schedule/annexure headers, Title-Case headings, and employment contract regression.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.pdf_extractor import PDFExtractor


@pytest.fixture(scope="module")
def extractor():
    return PDFExtractor()


# ── Test: Decimal & mixed headers → >= 8 segments ────────────────────

def test_mixed_headers_produces_enough_segments(extractor):
    """Text with '1.', '2.1', '2.1.1', '(a)', 'SCHEDULE 1', 'ANNEXURE A'
    headers should produce at least 8 segments."""
    text = """
Partner Agreement

1. Scope of Agreement
This clause describes the scope of the agreement between the two parties.

2. Obligations of Partner

2.1 Service Delivery
The Partner shall deliver all services in accordance with agreed SLAs.

2.1.1 Response Times
Critical incidents shall be responded to within 4 hours.

(a) Incident Classification
All incidents shall be classified according to severity levels defined herein.

(b) Escalation Procedures
Escalation shall follow the defined hierarchy.

2.2 Reporting Requirements
Monthly reports shall be submitted by the 5th of each month.

3. Payment Terms
Client shall pay all invoices within 30 days.

4. Intellectual Property
All IP created during the engagement shall be jointly owned.

SCHEDULE 1 — Fees
This schedule lists the applicable fee rates for all services.

ANNEXURE A — Service Levels
This annexure defines the target service levels and KPIs.

EXHIBIT B — Insurance Requirements
Contractor shall maintain professional indemnity insurance during the term.

APPENDIX C — Data Processing Addendum
The parties agree to the data processing terms set forth herein.

Governing Law
This agreement shall be governed by the laws of the State of New York.
"""
    clauses = extractor.segment_clauses(text)
    assert len(clauses) >= 8, f"Expected >= 8 clauses, got {len(clauses)}"
    for c in clauses:
        assert "id" in c
        assert "title" in c
        assert "content" in c
        assert "type" in c
        assert len(c["content"]) > 0


# ── Test: Title-Case unnumbered heading produces a segment ────────────

def test_title_case_heading_produces_segment(extractor):
    """A standalone Title-Case line followed by a longer paragraph
    should be treated as a clause header."""
    text = """SERVICES AGREEMENT

Services and Deliverables
The Contractor shall provide the following services and deliverables
in accordance with the specifications set forth in the Statement of Work
attached hereto as Exhibit A. All deliverables shall be subject to
acceptance testing by the Client.

Payment and Invoicing
Client shall pay Contractor within thirty days of receipt of an
accurate and undisputed invoice. All invoices shall reference the
applicable purchase order number.
"""
    clauses = extractor.segment_clauses(text)
    assert len(clauses) >= 2, f"Expected >= 2 clauses, got {len(clauses)}"

    # One of the clauses should have "Services and Deliverables" or
    # "Payment and Invoicing" in its title/content
    titles_and_content = " ".join(
        c["title"] + " " + c["content"] for c in clauses
    )
    assert "Services and Deliverables" in titles_and_content or \
           "Services" in titles_and_content, \
           f"No Services heading found: {[c['title'] for c in clauses]}"
    assert "Payment" in titles_and_content, \
           f"No Payment heading found: {[c['title'] for c in clauses]}"


# ── Test: Inline "(a)" mid-sentence does NOT split ────────────────────

def test_inline_lettered_ref_does_not_split(extractor):
    """An '(a)' appearing mid-paragraph (not at line start) should
    NOT trigger a clause split."""
    text = """1. General Provisions
The parties agree to the following terms: (a) all notices shall be in writing,
(b) no amendment shall be effective unless signed by both parties, and
(c) this agreement supersedes all prior agreements.

2. Term and Termination
This agreement shall commence on the Effective Date and continue for
a period of three years. Either party may terminate upon 30 days notice.
"""
    clauses = extractor.segment_clauses(text)
    # Should have ~2 clauses (1. General, 2. Term) — not split by mid-text (a), (b), (c)
    assert len(clauses) >= 2, f"Expected >= 2 clauses, got {len(clauses)}"
    assert len(clauses) <= 5, (
        f"Expected <= 5 clauses (inline (a) should not split), "
        f"got {len(clauses)}: {[c['title'] for c in clauses]}"
    )

    # The first clause should contain the inline (a), (b), (c) — not split them out
    first_clause = clauses[0]["content"]
    assert "(a)" in first_clause, "First clause lost inline (a)"
    assert "(b)" in first_clause, "First clause lost inline (b)"
    assert "(c)" in first_clause, "First clause lost inline (c)"


# ── Test: Employment-style numbered contract still segments correctly ─

def test_employment_numbered_contract(extractor):
    """A standard numbered employment contract with ~20 clauses should
    produce ~20 segments after splitting."""
    # Build a realistic 20-clause employment contract
    sections = []
    for i in range(1, 21):
        sections.append(
            f"{i}. Clause {i}\n"
            f"This is the detailed content of clause number {i}. "
            f"It describes the obligations and rights of both parties "
            f"with respect to the subject matter of this clause. "
            f"The provisions herein are binding and enforceable."
        )
    text = "EMPLOYMENT AGREEMENT\n\n" + "\n\n".join(sections)

    clauses = extractor.segment_clauses(text)
    assert len(clauses) >= 15, (
        f"Expected >= 15 clauses for 20-section contract, got {len(clauses)}"
    )
    assert len(clauses) <= 25, (
        f"Expected <= 25 clauses, got {len(clauses)} (over-splitting?)"
    )
    for c in clauses:
        assert len(c["content"]) >= 10, f"Clause {c['id']} too short"


# ── Test: Empty / short text returns single fallback clause ───────────

def test_empty_text_single_fallback(extractor):
    """Empty text should return a single fallback clause or empty list."""
    clauses = extractor.segment_clauses("")
    assert isinstance(clauses, list)
    # Should have 0 or 1 clause (fallback)
    assert len(clauses) <= 1, f"Expected <= 1 clause for empty text, got {len(clauses)}"


def test_very_short_text_single_clause(extractor):
    """Very short text should still produce valid output."""
    clauses = extractor.segment_clauses("Short text snippet.")
    assert isinstance(clauses, list)
    assert len(clauses) >= 1
    for c in clauses:
        assert "id" in c
        assert "content" in c


# ── Test: Schedule/Annexure headers detected ──────────────────────────

def test_schedule_and_annexure_headers(extractor):
    """SCHEDULE, ANNEXURE, EXHIBIT, APPENDIX headers should be detected
    as clause boundaries."""
    text = """MASTER SERVICES AGREEMENT

1. Definitions
Capitalized terms shall have the meanings set forth below.

SCHEDULE 1
Fee Schedule for all services provided under this agreement.

2. Services
Provider shall deliver the services described in Schedule 1.

SCHEDULE 2
Service Level Agreement defining uptime and response time commitments.

ANNEXURE A
Data Processing Terms as required by applicable privacy law.

EXHIBIT B
Form of Statement of Work to be executed for each project.

APPENDIX C
Insurance requirements and minimum coverage amounts.
"""
    clauses = extractor.segment_clauses(text)
    assert len(clauses) >= 6, (
        f"Expected >= 6 clauses (including schedule/annexure), got {len(clauses)}"
    )
    titles = [c["title"] for c in clauses]
    # At least one schedule/annexure/exhibit/appendix should appear
    found = any(
        "SCHEDULE" in t or "ANNEXURE" in t or "EXHIBIT" in t or "APPENDIX" in t
        for t in titles
    )
    assert found, f"No schedule/annexure/exhibit/appendix detected in: {titles}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
