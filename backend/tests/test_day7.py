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

from app.services.rag_service import RAGService, COLLECTION_NAME


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
        cls.rag = RAGService()

    # ── JSON file integrity ─────────────────────────────────────

    def test_total_clause_count(self):
        """We should have 20 clauses (10 original + 10 employment)."""
        assert len(self.all_clauses) == 20, (
            f"Expected 20 clauses, got {len(self.all_clauses)}"
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
        """Search for notice period should return employment notice clause."""
        results = self.rag.find_similar_clauses(
            query_text="The employee must provide 15 days notice period before resignation.",
            top_k=5,
        )
        assert len(results) > 0, "No results for notice period query"
        titles = [r["title"] for r in results]
        notice_matches = [t for t in titles if "notice" in t.lower()]
        assert len(notice_matches) >= 1, (
            f"No notice clause in results. Got: {titles[:3]}"
        )

    def test_employment_salary_search(self):
        """Search for salary payment should match employment salary clause."""
        results = self.rag.find_similar_clauses(
            query_text="Salary shall be paid by the 15th of every month with a detailed payslip.",
            top_k=5,
        )
        assert len(results) > 0, "No results for salary payment query"
        titles = [r["title"] for r in results]
        salary_matches = [t for t in titles if "salary" in t.lower() or "payment" in t.lower()]
        assert len(salary_matches) >= 1, (
            f"No salary/payment clause in results. Got: {titles[:3]}"
        )

    def test_employment_gratuity_search(self):
        """Search for gratuity should match employment gratuity clause."""
        results = self.rag.find_similar_clauses(
            query_text="Gratuity will be paid as per the Payment of Gratuity Act to the employee.",
            top_k=5,
        )
        assert len(results) > 0, "No results for gratuity query"
        titles = [r["title"] for r in results]
        gratuity_matches = [t for t in titles if "gratuity" in t.lower()]
        assert len(gratuity_matches) >= 1, (
            f"No gratuity clause in results. Got: {titles[:3]}"
        )

    def test_employment_noncompete_search(self):
        """Search for non-compete should match employment non-compete clause."""
        results = self.rag.find_similar_clauses(
            query_text="The employee shall not work for any competitor for 2 years after leaving the company.",
            top_k=5,
        )
        assert len(results) > 0, "No results for non-compete query"
        titles = [r["title"] for r in results]
        # Either employment non-compete or original non_compete
        compete_matches = [t for t in titles if "non-compete" in t.lower() or "solicitation" in t.lower() or "compete" in t.lower()]
        assert len(compete_matches) >= 1, (
            f"No non-compete clause in results. Got: {titles[:3]}"
        )

    def test_employment_confidentiality_search(self):
        """Search for confidentiality should match employment confidentiality clause."""
        results = self.rag.find_similar_clauses(
            query_text="Employee shall keep all company information confidential for 5 years after termination.",
            top_k=5,
        )
        assert len(results) > 0, "No results for confidentiality query"
        titles = [r["title"] for r in results]
        conf_matches = [t for t in titles if "confidential" in t.lower()]
        assert len(conf_matches) >= 1, (
            f"No confidentiality clause in results. Got: {titles[:3]}"
        )

    def test_employment_hours_search(self):
        """Search for working hours should match employment hours clause."""
        results = self.rag.find_similar_clauses(
            query_text="The working hours are 9 AM to 6 PM, Monday through Saturday, with overtime as required.",
            top_k=5,
        )
        assert len(results) > 0, "No results for working hours query"
        titles = [r["title"] for r in results]
        hours_matches = [t for t in titles if "hours" in t.lower() or "working" in t.lower()]
        assert len(hours_matches) >= 1, (
            f"No working hours clause in results. Got: {titles[:3]}"
        )

    def test_employment_ip_search(self):
        """Search for IP assignment should match employment IP clause."""
        results = self.rag.find_similar_clauses(
            query_text="All intellectual property created by the employee during employment belongs to the company.",
            top_k=5,
        )
        assert len(results) > 0, "No results for IP assignment query"
        titles = [r["title"] for r in results]
        ip_matches = [t for t in titles if "ip" in t.lower() or "intellectual" in t.lower()]
        assert len(ip_matches) >= 1, (
            f"No IP clause in results. Got: {titles[:3]}"
        )

    # ── RAG comparison quality ──────────────────────────────────

    def test_compare_employment_clause_returns_alternatives(self):
        """compare_clause should return fair alternatives for an employment clause."""
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
            # If seeded, should have at least some clauses
            if count > 0:
                assert count >= 10, (
                    f"Expected at least 10 clauses in collection, got {count}"
                )
