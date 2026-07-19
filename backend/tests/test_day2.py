"""
ContractGuard - Day 2 Tests
Verify RAG service: Qdrant connection, embeddings, CRUD, similarity search.
"""

import sys
from pathlib import Path

import pytest

# Ensure backend/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rag_service import RAGService, COLLECTION_NAME

# ── Helpers ───────────────────────────────────────────────────────────────

def _skip_if_no_qdrant(rag: RAGService) -> None:
    """Skip the current test if Qdrant is not reachable."""
    if not _qdrant_is_up(rag):
        pytest.skip("Qdrant is not running. Start it with: docker run -d -p 6333:6333 qdrant/qdrant")


def _qdrant_is_up(rag: RAGService) -> bool:
    """Check Qdrant connectivity without raising."""
    try:
        rag.qdrant.get_collections()
        return True
    except Exception:
        return False


def _ensure_clean_collection(rag: RAGService) -> None:
    """Create a fresh collection for testing."""
    if not _qdrant_is_up(rag):
        return
    rag.create_collection(force_recreate=True)


# ── Fixture ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def rag():
    """Module-level RAGService instance."""
    svc = RAGService()
    return svc


# ── Tests ──────────────────────────────────────────────────────────────────

class TestQdrantConnection:
    """Tests for Qdrant connectivity and collection management."""

    def test_qdrant_connection(self, rag):
        """Should connect to Qdrant successfully."""
        if not _qdrant_is_up(rag):
            pytest.skip("Qdrant not running")
        collections = rag.qdrant.get_collections()
        assert collections is not None
        assert hasattr(collections, "collections")

    def test_create_collection(self, rag):
        """Should create the fair_clauses collection."""
        _skip_if_no_qdrant(rag)
        result = rag.create_collection(force_recreate=True)
        assert result is True

        # Verify it exists
        names = [c.name for c in rag.qdrant.get_collections().collections]
        assert COLLECTION_NAME in names

    def test_collection_exists(self, rag):
        """Should correctly report collection existence."""
        _skip_if_no_qdrant(rag)
        _ensure_clean_collection(rag)
        assert rag.collection_exists() is True

    def test_health_check(self, rag):
        """Should return health status dict."""
        _skip_if_no_qdrant(rag)
        _ensure_clean_collection(rag)
        health = rag.health_check()
        assert "qdrant_status" in health
        assert health["qdrant_status"] == "connected"
        assert "collection_exists" in health
        assert "clause_count" in health

    def test_health_check_no_qdrant(self):
        """Should report disconnected when Qdrant is unreachable."""
        # Switch to remote mode with bad host to test disconnection handling
        from app.core.config import settings as s
        original_mode = s.QDRANT_MODE
        original_host = s.QDRANT_HOST
        s.QDRANT_MODE = "remote"
        s.QDRANT_HOST = "255.255.255.255"  # unreachable
        try:
            bad_rag = RAGService()
            health = bad_rag.health_check()
            assert health["qdrant_status"] == "disconnected"
        finally:
            s.QDRANT_MODE = original_mode
            s.QDRANT_HOST = original_host


class TestEmbeddings:
    """Tests for sentence-transformer embedding generation."""

    def test_embedding_dimension(self, rag):
        """Should generate 384-dim vectors (all-MiniLM-L6-v2)."""
        # Embedding doesn't need Qdrant
        vec = rag.generate_embedding("This is a test clause about payment terms.")
        assert isinstance(vec, list)
        assert len(vec) == 384
        assert all(isinstance(v, float) for v in vec)

    def test_embedding_normalized(self, rag):
        """Should produce unit vectors (cosine normalized)."""
        import math
        vec = rag.generate_embedding("Test content for normalization check.")
        magnitude = math.sqrt(sum(v * v for v in vec))
        # Normalized vectors have magnitude ≈ 1.0
        assert 0.99 < magnitude < 1.01, f"Expected ~1.0, got {magnitude}"

    def test_embedding_empty_text(self, rag):
        """Should raise ValueError for empty text."""
        with pytest.raises(ValueError, match="empty"):
            rag.generate_embedding("")
        with pytest.raises(ValueError, match="empty"):
            rag.generate_embedding("   ")

    def test_embedding_consistency(self, rag):
        """Same input should produce the same vector."""
        text = "The Consultant shall be paid within 30 days."
        v1 = rag.generate_embedding(text)
        v2 = rag.generate_embedding(text)
        assert v1 == pytest.approx(v2, abs=1e-5)


class TestClauseCRUD:
    """Tests for adding & retrieving fair clauses."""

    def test_add_fair_clause(self, rag):
        """Should add a clause and retrieve it."""
        _skip_if_no_qdrant(rag)
        _ensure_clean_collection(rag)

        cid = rag.add_fair_clause(
            clause_type="payment",
            title="Fair Payment Clause",
            content="Client shall pay within 30 days of invoice receipt.",
        )
        assert cid is not None
        assert len(cid) > 0

        # Retrieve and verify
        clause = rag.get_clause_by_id(cid)
        assert clause is not None
        assert clause["type"] == "payment"
        assert "30 days" in clause["content"]

    def test_add_multiple_clauses(self, rag):
        """Should add and retrieve multiple clauses."""
        _skip_if_no_qdrant(rag)
        _ensure_clean_collection(rag)

        types = ["payment", "termination", "liability", "confidentiality"]
        ids = []
        for t in types:
            cid = rag.add_fair_clause(
                clause_type=t,
                title=f"Test {t.title()} Clause",
                content=f"This is a fair {t} clause for testing purposes. It contains balanced terms.",
            )
            ids.append(cid)

        all_clauses = rag.get_all_clauses()
        assert len(all_clauses) == len(types)

        for t in types:
            found = [c for c in all_clauses if c["type"] == t]
            assert len(found) == 1, f"Expected 1 clause of type '{t}', got {len(found)}"

    def test_get_nonexistent_clause(self, rag):
        """Should return None for non-existent clause ID."""
        _skip_if_no_qdrant(rag)
        _ensure_clean_collection(rag)
        result = rag.get_clause_by_id("nonexistent-id-12345")
        assert result is None

    def test_delete_all_clauses(self, rag):
        """Should delete all clauses and leave empty collection."""
        _skip_if_no_qdrant(rag)
        _ensure_clean_collection(rag)

        # Add a few
        for i in range(3):
            rag.add_fair_clause("general", f"Test {i}", f"Test content {i}")

        assert len(rag.get_all_clauses()) == 3

        # Delete all
        deleted = rag.delete_all_clauses()
        assert deleted > 0

        remaining = rag.get_all_clauses()
        assert len(remaining) == 0


class TestSimilaritySearch:
    """Tests for semantic similarity search."""

    @pytest.fixture(autouse=True)
    def setup_seed(self, rag):
        """Seed test data before each test in this class."""
        if not _qdrant_is_up(rag):
            return

        _ensure_clean_collection(rag)

        # Add diverse test clauses
        test_clauses = [
            ("payment", "Payment Within 30 Days", "Client shall pay all invoices within 30 days of receipt. Late payments accrue interest at 1% per month."),
            ("payment", "Advance Payment", "Client shall pay a 50% advance before work begins and the remaining 50% upon completion."),
            ("termination", "Mutual Termination", "Either party may terminate this agreement upon 60 days written notice or immediately for material breach."),
            ("liability", "Capped Liability", "Neither party's total liability shall exceed the fees paid in the preceding 12 months. No consequential damages."),
            ("confidentiality", "Mutual NDA", "Both parties agree to protect each other's confidential information with reasonable care for 5 years after disclosure."),
        ]

        for ctype, title, content in test_clauses:
            rag.add_fair_clause(ctype, title, content)

    def test_similarity_search_basic(self, rag):
        """Should return relevant results for a query."""
        _skip_if_no_qdrant(rag)

        query = "How should payments be handled in this contract? Client needs to pay within reasonable time."
        results = rag.find_similar_clauses(query, top_k=2)
        assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"
        assert results[0]["score"] > 0.0
        assert "content" in results[0]
        assert "title" in results[0]
        assert "type" in results[0]

    def test_similarity_search_with_type_filter(self, rag):
        """Should return only clauses of the specified type."""
        _skip_if_no_qdrant(rag)

        results = rag.find_similar_clauses(
            query_text="Termination of the contract should require notice.",
            clause_type="termination",
            top_k=3,
        )
        assert len(results) >= 1
        for r in results:
            assert r["type"] == "termination", f"Expected termination, got {r['type']}"

    def test_similarity_search_empty_query(self, rag):
        """Should return empty list for empty query."""
        _skip_if_no_qdrant(rag)
        results = rag.find_similar_clauses("", top_k=3)
        assert results == []

    def test_compare_clause(self, rag):
        """Should compare a contract clause and return alternatives."""
        _skip_if_no_qdrant(rag)

        contract_clause = {
            "id": "test_clause_001",
            "title": "Payment Terms",
            "content": "Client shall pay invoices within 45 days. Interest at 1.5% per month applies on late payments.",
            "type": "payment",
        }

        result = rag.compare_clause(contract_clause)
        assert "clause_id" in result
        assert result["clause_id"] == "test_clause_001"
        assert "fair_alternatives" in result
        assert "comparison_notes" in result
        assert isinstance(result["fair_alternatives"], list)
        # Should find at least 1 payment-related alternative
        assert len(result["fair_alternatives"]) >= 1
        # Comparison notes should mention the 1.5% interest red flag
        assert "1.5%" in result["comparison_notes"] or "fair" in result["comparison_notes"].lower()

    def test_compare_empty_clause(self, rag):
        """Should handle empty clause gracefully."""
        _skip_if_no_qdrant(rag)

        result = rag.compare_clause({
            "id": "empty_001",
            "title": "",
            "content": "",
            "type": "general",
        })
        assert result["clause_id"] == "empty_001"
        assert result["fair_alternatives"] == []


class TestEmbeddingModelLoad:
    """Test that the embedding model loads correctly (or falls back)."""

    def test_encoder_loaded(self, rag):
        """Should load the sentence-transformer model or use fallback."""
        encoder = rag.encoder
        if encoder is None:
            # Model not cached locally — fallback mode is active.
            # Verify fallback works by generating an embedding.
            vec = rag.generate_embedding("Test fallback embedding generation.")
            assert len(vec) == 384
        else:
            dim = encoder.get_sentence_embedding_dimension()
            assert dim == 384, f"Expected 384, got {dim}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
