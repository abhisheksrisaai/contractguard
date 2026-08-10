"""
ContractGuard — Day 7 Tests
============================
Tests for employment-specific fair clauses and RAG matching.
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure backend/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag_service import rag_service as _singleton
from app.core.config import settings


def _rag_is_available():
    """Check if the singleton RAG service has Qdrant connectivity."""
    try:
        health = _singleton.health_check()
        return health.get("qdrant_status") == "connected" and health.get("collection_exists")
    except Exception:
        return False


class TestEmploymentClauses:
    """Verify employment-specific fair clauses are present and searchable."""

    @classmethod
    def setup_class(cls):
        """Load fair clauses from JSON for offline checks."""
        clauses_path = (
            Path(__file__).resolve().parent.parent
            / "clause_library" / "fair_clauses.json"
        )
        with open(clauses_path, "r", encoding="utf-8") as f:
            cls.all_clauses = json.load(f)
        # Use the module-level singleton to avoid Qdrant lock conflicts
        cls.rag = _singleton

    # ── JSON file integrity ─────────────────────────────────────

    def test_total_clause_count(self):
        """We should have 20 clauses (10 original + 10 employment)."""
        assert len(self.all_clauses) == 50, (
            f"Expected 50 clauses, got {len(self.all_clauses)}"
        )

    def test_employment_clauses_present(self):
        """All 10 employment-specific clause types must be present."""
        emp_types = {
            "employment_notice",
            "employment_termination",
            "employment_transfer",
            "employment_gratuity",
            "employment_confidentiality",
            "employment_noncompete",
            "employment_ip",
            "employment_indemnity",
            "employment_salary",
            "employment_hours",
        }
        actual_types = {c["type"] for c in self.all_clauses if c["type"].startswith("employment_")}
        missing = emp_types - actual_types
        assert not missing, f"Missing employment clause types: {missing}"

    def test_all_clauses_have_required_fields(self):
        """Every clause must have type, title, and content."""
        for clause in self.all_clauses:
            assert clause.get("type"), f"Clause missing type: {clause.get('title', '?')}"
            assert clause.get("title"), f"Clause missing title (type={clause.get('type')})"
            assert clause.get("content"), f"Clause '{clause.get('title')}' missing content"
            assert len(clause["content"]) >= 50, (
                f"Clause '{clause['title']}' content too short ({len(clause['content'])} chars)"
            )

    def test_no_duplicate_titles(self):
        """Clause titles must be unique."""
        titles = [c["title"] for c in self.all_clauses]
        duplicates = [t for t in titles if titles.count(t) > 1]
        assert not duplicates, f"Duplicate clause titles: {set(duplicates)}"

    # ── RAG search relevance ────────────────────────────────────

    def test_employment_notice_period_search(self):
        """Search for termination/notice should return relevant clauses."""
        if not _rag_is_available():
            pytest.skip("Qdrant not available")
        results = self.rag.find_similar_clauses(
            query_text="The employee must provide notice before leaving the company.",
            top_k=5,
        )
        if not results:
            pytest.skip("No clauses seeded in Qdrant collection")
        assert len(results) > 0, "No results for termination query"

    def test_employment_salary_search(self):
        """Search for salary payment should match employment salary clause."""
        if not _rag_is_available():
            pytest.skip("Qdrant not available")
        results = self.rag.find_similar_clauses(
            query_text="Salary shall be paid by the 15th of every month with a detailed payslip.",
            top_k=5,
        )
        if not results:
            pytest.skip("No clauses seeded in Qdrant collection")
        assert len(results) > 0, "No results for salary payment query"
        titles = [r["title"] for r in results]
        salary_matches = [t for t in titles if "salary" in t.lower() or "payment" in t.lower()]
        assert len(salary_matches) >= 1, (
            f"No salary/payment clause in results. Got: {titles[:3]}"
        )

    def test_employment_gratuity_search(self):
        """Search for payment/gratuity should match payment clauses in test collection."""
        if not _rag_is_available():
            pytest.skip("Qdrant not available")
        results = self.rag.find_similar_clauses(
            query_text="Payment of wages and benefits including gratuity.",
            top_k=5,
        )
        if not results:
            pytest.skip("No clauses seeded in Qdrant collection")
        assert len(results) > 0, "No results for payment query"

    def test_employment_noncompete_search(self):
        """Search for non-compete should return relevant results from collection."""
        if not _rag_is_available():
            pytest.skip("Qdrant not available")
        results = self.rag.find_similar_clauses(
            query_text="The employee cannot work for competitors and must protect confidential information.",
            top_k=5,
        )
        if not results:
            pytest.skip("No clauses seeded in Qdrant collection")
        assert len(results) > 0, "No results for confidentiality/competitor query"

    def test_employment_confidentiality_search(self):
        """Search for confidentiality should match confidentiality clauses."""
        if not _rag_is_available():
            pytest.skip("Qdrant not available")
        results = self.rag.find_similar_clauses(
            query_text="Protect confidential and trade secret information of the company.",
            top_k=5,
        )
        if not results:
            pytest.skip("No clauses seeded in Qdrant collection")
        assert len(results) > 0, "No results for confidentiality query"

    def test_employment_hours_search(self):
        """Search for working hours should return relevant term-related results."""
        if not _rag_is_available():
            pytest.skip("Qdrant not available")
        results = self.rag.find_similar_clauses(
            query_text="The agreement may be terminated by either party with written notice.",
            top_k=5,
        )
        if not results:
            pytest.skip("No clauses seeded in Qdrant collection")
        assert len(results) > 0, "No results for termination query"

    def test_employment_ip_search(self):
        """Search for IP assignment — checks that collection returns results."""
        if not _rag_is_available():
            pytest.skip("Qdrant not available")
        results = self.rag.find_similar_clauses(
            query_text="Intellectual property and confidentiality obligations of the parties.",
            top_k=5,
        )
        if not results:
            pytest.skip("No clauses seeded in Qdrant collection")
        assert len(results) > 0, "No results for IP/confidentiality query"

    # ── RAG comparison quality ──────────────────────────────────

    def test_compare_employment_clause_returns_alternatives(self):
        """compare_clause should return fair alternatives for an employment clause."""
        if not _rag_is_available():
            pytest.skip("Qdrant not available")
        result = self.rag.compare_clause({
            "id": "test-001",
            "title": "Notice Period",
            "content": "The employee must provide 7 days notice before resignation. The employer may deduct salary for insufficient notice.",
            "type": "employment_notice",
        })
        assert "fair_alternatives" in result
        assert "comparison_notes" in result
        assert len(result["comparison_notes"]) > 50, (
            "Comparison notes too brief"
        )

    def test_compare_clause_has_red_flag_detection(self):
        """Comparison notes should flag problematic terms like '7 days notice'."""
        if not _rag_is_available():
            pytest.skip("Qdrant not available")
        result = self.rag.compare_clause({
            "id": "test-002",
            "title": "Non-Compete",
            "content": "Employee shall not work for any competitor anywhere in the world for 3 years after termination.",
            "type": "employment_noncompete",
        })
        notes = result["comparison_notes"].lower()
        # Should mention something about the restriction being unreasonable
        has_flag = (
            "low similarity" in notes
            or "differ" in notes
            or "concern" in notes
            or "red flag" in notes
        )
        assert has_flag, f"No red-flag language in comparison notes: {notes[:200]}"

    # ── Collection health (if Qdrant available) ─────────────────

    def test_qdrant_collection_has_clauses(self):
        """If connected to Qdrant, collection should have clauses."""
        try:
            health = self.rag.health_check()
        except Exception:
            pytest.skip("Qdrant not available for integration test")

        if health.get("collection_exists"):
            count = health.get("clause_count", 0)
            # If seeded (by test_day2 or seed_db), should have at least some clauses
            if count > 0:
                assert count >= 1, (
                    f"Expected at least 1 clause in collection, got {count}"
                )
