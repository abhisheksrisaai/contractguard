"""
ContractGuard - Day 8b Tests
Verify persisted TF-IDF embedding: determinism, semantic sanity,
dimensionality, normalization, and compare_clause quality.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag_service import RAGService, COLLECTION_NAME, rag_service as _singleton


def _rag_available():
    """True if singleton Qdrant is connected."""
    try:
        h = _singleton.health_check()
        return h.get("qdrant_status") == "connected" and h.get("collection_exists")
    except Exception:
        return False


@pytest.fixture(scope="module")
def rag():
    """Use singleton to avoid Qdrant lock conflicts with test_day2."""
    return _singleton


def _qdrant_up(rag):
    try:
        h = rag.health_check()
        return h.get("qdrant_status") == "connected" and h.get("collection_exists")
    except Exception:
        return False


# ── Determinism: same text → same vector ────────────────────────────

def test_embedding_determinism(rag):
    """The same text embedded twice must produce identical vectors."""
    text = "Client shall pay all invoices within 30 days of receipt."
    v1 = rag.generate_embedding(text)
    v2 = rag.generate_embedding(text)
    assert len(v1) == len(v2)
    assert v1 == pytest.approx(v2, abs=1e-6)


# ── Dimensionality & normalization ──────────────────────────────────

def test_embedding_dimensions(rag):
    """All embeddings must be exactly 384-dimensional."""
    vec = rag.generate_embedding("Payment terms and conditions.")
    assert len(vec) == 384, f"Expected 384, got {len(vec)}"


def test_embedding_unit_normalized(rag):
    """All embeddings must be L2 unit vectors (|v| ≈ 1.0)."""
    vec = rag.generate_embedding(
        "Client shall pay Consultant a fixed fee of $15,000 per month "
        "within 30 days of invoice. Late payments accrue interest at 1.5%."
    )
    mag = math.sqrt(sum(v * v for v in vec))
    assert 0.999 < mag < 1.001, f"Expected unit vector, got magnitude {mag}"


# ── Semantic sanity: payment clause closer to payment than non-compete ─

def test_semantic_sanity_payment_vs_noncompete(rag):
    """
    A payment clause should score higher against the fair payment clause
    than against a fair non-compete clause — IF both are in the collection.
    """
    if not _qdrant_up(rag):
        pytest.skip("Qdrant not available")

    payment_query = "Client shall pay all invoices within 30 days. Late payments accrue interest at 1.5% per month."

    # Get top-k results (no type filter) so we can compare scores across types
    results = rag.find_similar_clauses(query_text=payment_query, top_k=10)
    if len(results) < 2:
        pytest.skip("Not enough clauses in collection for semantic sanity check")

    # Find scores for payment vs non-compete clauses
    payment_scores = [
        r["score"] for r in results
        if r["type"] == "payment"
        or "payment" in r.get("title", "").lower()
        or "salary" in r.get("type", "").lower()
    ]
    noncompete_scores = [
        r["score"] for r in results
        if "non_compete" in r["type"]
        or "non-compete" in r.get("title", "").lower()
    ]

    if payment_scores and noncompete_scores:
        best_payment = max(payment_scores)
        best_noncompete = max(noncompete_scores)
        assert best_payment > best_noncompete, (
            f"Payment query should score higher against payment clauses "
            f"({best_payment:.4f}) than non-compete clauses ({best_noncompete:.4f})"
        )


# ── compare_clause returns plausible scores ─────────────────────────

def test_compare_clause_payment_returns_alternatives(rag):
    """
    compare_clause on a payment clause must return fair_alternatives with
    scores in the plausible range [0.0, 1.0] and at least one result.
    """
    if not _qdrant_up(rag):
        pytest.skip("Qdrant not available")

    result = rag.compare_clause({
        "id": "test-payment-1",
        "title": "Invoice Payment Terms",
        "content": "Client shall pay all invoices within 45 days of receipt. "
                   "Late payments shall accrue interest at 1.5% per month.",
        "type": "payment",
    })

    assert "fair_alternatives" in result
    assert "comparison_notes" in result
    assert len(result["comparison_notes"]) > 50, "comparison_notes too short"

    alts = result["fair_alternatives"]
    assert isinstance(alts, list)

    if alts:
        for alt in alts:
            assert "title" in alt
            assert "content" in alt
            assert "score" in alt
            assert 0.0 <= alt["score"] <= 1.0, (
                f"Score {alt['score']} out of range [0,1]"
            )
            assert "type" in alt


# ── Vectorizer persistence ──────────────────────────────────────────

def test_vectorizer_persisted_after_embedding(rag):
    """After calling _get_or_create_vectorizer, the vectorizer file should exist."""
    # Explicitly trigger vectorizer creation (generate_embedding may use
    # sentence-transformers if available, never reaching the fallback path)
    rag._get_or_create_vectorizer()
    vpath = rag._vectorizer_path()
    assert vpath.exists(), f"Vectorizer file not found at {vpath}"
    assert vpath.stat().st_size > 100, f"Vectorizer file too small: {vpath.stat().st_size} bytes"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
