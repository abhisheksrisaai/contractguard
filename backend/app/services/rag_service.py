"""
ContractGuard - RAG Service (Retrieval-Augmented Generation)

Handles:
- Vector embeddings via sentence-transformers
- Storage & retrieval in Qdrant vector DB
- Finding similar fair clauses for contract clause comparison
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    CollectionStatus,
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSelectorInclude,
    PointStruct,
    Record,
    VectorParams,
)

# Try to import sentence-transformers; fall back to TF-IDF if unavailable
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None  # type: ignore
    HAS_SENTENCE_TRANSFORMERS = False

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
COLLECTION_NAME = "fair_clauses"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2


class RAGService:
    """
    Retrieval-Augmented Generation service for fair contract clauses.

    Uses:
    - Qdrant for vector storage & similarity search
    - sentence-transformers/all-MiniLM-L6-v2 for embeddings
    """

    def __init__(self) -> None:
        self._qdrant: Optional[QdrantClient] = None
        self._encoder: Optional[SentenceTransformer] = None

    # ── Qdrant Client ────────────────────────────────────────────────

    @property
    def qdrant(self) -> QdrantClient:
        """Lazy-initialize Qdrant client (remote or local mode)."""
        if self._qdrant is None:
            if settings.QDRANT_MODE == "local":
                # ── Local / embedded mode (no Docker needed) ─────
                local_path = settings.QDRANT_LOCAL_PATH
                if not local_path:
                    local_path = str(settings.project_root / "qdrant_data")
                logger.info("Opening Qdrant in LOCAL mode at: %s", local_path)
                try:
                    self._qdrant = QdrantClient(path=local_path)
                    self._qdrant.get_collections()
                    logger.info("Qdrant local storage ready.")
                except Exception as exc:
                    logger.error("Failed to open local Qdrant: %s", exc)
                    raise ConnectionError(
                        f"Cannot open local Qdrant at {local_path}. Error: {exc}"
                    ) from exc
            else:
                # ── Remote / Docker mode ──────────────────────────
                logger.info(
                    "Connecting to Qdrant at %s:%d ...",
                    settings.QDRANT_HOST,
                    settings.QDRANT_PORT,
                )
                try:
                    self._qdrant = QdrantClient(
                        host=settings.QDRANT_HOST,
                        port=settings.QDRANT_PORT,
                        timeout=10.0,
                    )
                    self._qdrant.get_collections()
                    logger.info("Qdrant remote connection established.")
                except Exception as exc:
                    logger.error("Failed to connect to Qdrant: %s", exc)
                    raise ConnectionError(
                        f"Cannot connect to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}. "
                        f"Ensure Qdrant is running (docker run -p 6333:6333 qdrant/qdrant). "
                        f"Error: {exc}"
                    ) from exc
        return self._qdrant

    @property
    def encoder(self):
        """Lazy-load the sentence-transformer embedding model.
        Returns None if model fails to load or package not installed,
        triggering TF-IDF fallback."""
        if self._encoder is None:
            if not HAS_SENTENCE_TRANSFORMERS:
                logger.info("sentence-transformers not installed. Using TF-IDF fallback.")
                self._encoder = None
                return None

            model_name = settings.EMBEDDING_MODEL.replace("sentence-transformers/", "")
            logger.info("Loading embedding model: %s ...", model_name)

            import os
            import glob
            # Check if model weight files exist in cache
            cache_root = os.path.expanduser("~/.cache/huggingface/hub")
            model_blobs = os.path.join(
                cache_root, "models--sentence-transformers--all-MiniLM-L6-v2", "blobs"
            )
            # Model is cached if we have blob files > 1MB (actual weights, not just configs)
            has_weights = False
            if os.path.isdir(model_blobs):
                for f in os.listdir(model_blobs):
                    fpath = os.path.join(model_blobs, f)
                    if os.path.isfile(fpath) and os.path.getsize(fpath) > 1_000_000:
                        has_weights = True
                        break

            if not has_weights:
                logger.warning(
                    "Model not cached. Using TF-IDF fallback. Run:"
                    " python -c 'from sentence_transformers import SentenceTransformer;"
                    " SentenceTransformer(\"%s\")'",
                    settings.EMBEDDING_MODEL,
                )
                self._encoder = None
            else:
                try:
                    self._encoder = SentenceTransformer(
                        settings.EMBEDDING_MODEL,
                        device="cpu",
                    )
                    logger.info("Model loaded. Dim: %d", self._encoder.get_sentence_embedding_dimension())
                except Exception as exc:
                    logger.warning("Failed to load model: %s. Using TF-IDF fallback.", exc)
                    self._encoder = None

        return self._encoder

    def _fallback_embedding(self, text: str) -> List[float]:
        """
        Lightweight TF-IDF + SVD fallback embedding (no GPU/models needed).
        Produces 384-dim vectors for compatibility.
        """
        import hashlib
        # Use TF-IDF for semantic representation
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD

        # For a single text, we need to fit on the fly.
        # We create a small "corpus" from the text + dummy background
        corpus = [
            "payment fee compensation invoice price amount due",
            "termination cancel end agreement notice period dissolve",
            "liability indemnification damages loss cap limit",
            "confidential non-disclosure trade secret proprietary",
            "intellectual property copyright patent trademark ownership",
            "data protection privacy personal gdpr processing breach",
            text,
        ]
        tfidf = TfidfVectorizer(max_features=500, stop_words="english")
        tfidf_matrix = tfidf.fit_transform(corpus)

        # Reduce to 384 dims via SVD
        n_components = min(384, tfidf_matrix.shape[1] - 1, tfidf_matrix.shape[0] - 1)
        if n_components < 2:
            # Fallback: hash-based deterministic vector
            h = hashlib.sha256(text.encode())
            digest_bytes = h.digest()
            vec = []
            for i in range(384):
                b = digest_bytes[i % len(digest_bytes)]
                vec.append((b / 127.5) - 1.0)  # normalize to [-1, 1]
            # Normalize to unit vector
            import math
            mag = math.sqrt(sum(v * v for v in vec))
            return [v / mag for v in vec]

        svd = TruncatedSVD(n_components=n_components, random_state=42)
        reduced = svd.fit_transform(tfidf_matrix)
        # Return the embedding for the last row (our text)
        vec = reduced[-1].tolist()
        # Pad to 384 if needed
        if len(vec) < 384:
            vec += [0.0] * (384 - len(vec))
        # Normalize
        import math
        mag = math.sqrt(sum(v * v for v in vec))
        if mag > 0:
            vec = [v / mag for v in vec]
        return vec

    # ── Collection Management ────────────────────────────────────────

    def create_collection(self, force_recreate: bool = False) -> bool:
        """
        Create (or verify) the fair_clauses collection in Qdrant.

        Args:
            force_recreate: If True, delete existing collection and recreate.

        Returns:
            True if collection now exists.
        """
        collections = [c.name for c in self.qdrant.get_collections().collections]

        if COLLECTION_NAME in collections:
            if force_recreate:
                logger.info("Deleting existing collection '%s'...", COLLECTION_NAME)
                self.qdrant.delete_collection(COLLECTION_NAME)
            else:
                logger.info("Collection '%s' already exists.", COLLECTION_NAME)
                return True

        logger.info(
            "Creating collection '%s' (vector_size=%d, distance=%s)...",
            COLLECTION_NAME,
            VECTOR_SIZE,
            Distance.COSINE,
        )
        self.qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Collection '%s' created successfully.", COLLECTION_NAME)
        return True

    def collection_exists(self) -> bool:
        """Check whether the fair_clauses collection exists."""
        names = [c.name for c in self.qdrant.get_collections().collections]
        return COLLECTION_NAME in names

    # ── Embedding Generation ─────────────────────────────────────────

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a vector embedding for a text string.

        Uses sentence-transformer model if available; falls back to
        TF-IDF + SVD if the model fails to load.

        Args:
            text: Input text to embed.

        Returns:
            List of floats (384-dim for all-MiniLM-L6-v2).
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text.")

        truncated = text[:2000]

        # Try sentence-transformer first
        try:
            enc = self.encoder
            if enc is not None:
                embedding = enc.encode(truncated, normalize_embeddings=True)
                return embedding.tolist()
        except Exception as exc:
            logger.warning("Sentence-transformer encode failed: %s. Using fallback.", exc)

        # Fallback to TF-IDF + SVD
        return self._fallback_embedding(truncated)

    # ── CRUD Operations ──────────────────────────────────────────────

    def add_fair_clause(
        self,
        clause_type: str,
        title: str,
        content: str,
        clause_id: Optional[str] = None,
    ) -> str:
        """
        Add a fair clause to the Qdrant collection.

        Args:
            clause_type: Type of clause (payment, termination, etc.)
            title: Clause title.
            content: Clause body text.
            clause_id: Optional custom ID (auto-generated if not provided).

        Returns:
            The clause ID.
        """
        if clause_id is None:
            import uuid
            clause_id = str(uuid.uuid4())

        # Combine title + content for richer embedding
        combined = f"{title}\n{content}"
        vector = self.generate_embedding(combined)

        point = PointStruct(
            id=clause_id,
            vector=vector,
            payload={
                "type": clause_type,
                "title": title,
                "content": content,
            },
        )

        self.qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[point],
            wait=True,
        )

        logger.info("Added fair clause '%s' (id=%s, type=%s)", title[:60], clause_id, clause_type)
        return clause_id

    def get_clause_by_id(self, clause_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a clause by its ID.

        Args:
            clause_id: The clause UUID.

        Returns:
            Dict with type, title, content or None if not found.
        """
        try:
            records = self.qdrant.retrieve(
                collection_name=COLLECTION_NAME,
                ids=[clause_id],
                with_payload=True,
            )
            if records and records[0].payload:
                return {
                    "id": records[0].id,
                    "type": records[0].payload.get("type", ""),
                    "title": records[0].payload.get("title", ""),
                    "content": records[0].payload.get("content", ""),
                }
        except Exception as exc:
            logger.warning("Failed to retrieve clause %s: %s", clause_id, exc)
        return None

    def get_all_clauses(self) -> List[Dict[str, Any]]:
        """
        Retrieve all fair clauses from the collection.

        Returns:
            List of clause dicts.
        """
        try:
            records, _next_offset = self.qdrant.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                with_payload=True,
                with_vectors=False,
            )
            clauses = []
            for rec in records:
                if rec.payload:
                    clauses.append({
                        "id": rec.id,
                        "type": rec.payload.get("type", ""),
                        "title": rec.payload.get("title", ""),
                        "content": rec.payload.get("content", ""),
                    })
            return clauses
        except Exception as exc:
            logger.warning("Failed to scroll collection: %s", exc)
            return []

    def delete_all_clauses(self) -> int:
        """
        Delete all points from the collection.

        Returns:
            Number of points deleted (approximate).
        """
        try:
            # Get current count for reporting
            info = self.qdrant.get_collection(COLLECTION_NAME)
            count = info.points_count if info else 0

            self.qdrant.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(),  # empty filter = match all
            )
            logger.info("Deleted all clauses (was ~%d).", count)
            return count
        except Exception as exc:
            logger.warning("Failed to delete all clauses: %s", exc)
            return 0

    # ── Similarity Search ────────────────────────────────────────────

    def find_similar_clauses(
        self,
        query_text: str,
        clause_type: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find fair clauses similar to the query text.

        Args:
            query_text: The contract clause text to match against.
            clause_type: Optional filter to restrict search to a specific type.
            top_k: Number of results to return.

        Returns:
            List of dicts with id, type, title, content, and similarity score.
        """
        if not query_text or not query_text.strip():
            logger.warning("Empty query text for similarity search.")
            return []

        query_vector = self.generate_embedding(query_text)

        # Build optional filter
        query_filter = None
        if clause_type:
            query_filter = Filter(
                must=[FieldCondition(key="type", match=MatchValue(value=clause_type))]
            )

        try:
            # qdrant-client >= 1.10: query_points API
            results = self.qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=min(top_k, 50),
                query_filter=query_filter,
                with_payload=True,
            )
        except AttributeError:
            # Fallback for older qdrant-client versions
            results = self.qdrant.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                limit=min(top_k, 50),
                query_filter=query_filter,
                with_payload=True,
            )

        matches = []
        for hit in results.points if hasattr(results, 'points') else results:
            payload = hit.payload or {}
            matches.append({
                "id": hit.id,
                "type": payload.get("type", ""),
                "title": payload.get("title", ""),
                "content": payload.get("content", ""),
                "score": round(hit.score, 4),
            })

        logger.info(
            "Found %d similar clauses for query '%s...' (type=%s)",
            len(matches),
            query_text[:60],
            clause_type or "any",
        )
        return matches

    # ── Clause Comparison ────────────────────────────────────────────

    def compare_clause(self, contract_clause: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare a contract clause with similar fair clauses from the library.

        Args:
            contract_clause: Dict with keys id, title, content, type.

        Returns:
            Dict with clause_id, fair_alternatives (list), and comparison_notes.
        """
        clause_id = contract_clause.get("id", "unknown")
        clause_title = contract_clause.get("title", "")
        clause_content = contract_clause.get("content", "")
        clause_type = contract_clause.get("type", "general")

        logger.info("Comparing clause %s (type=%s)...", clause_id, clause_type)

        if not clause_content.strip():
            return {
                "clause_id": clause_id,
                "fair_alternatives": [],
                "comparison_notes": "Empty clause — nothing to compare.",
            }

        # Search first with type filter, then without as fallback
        alternatives = self.find_similar_clauses(
            query_text=clause_content,
            clause_type=clause_type,
            top_k=3,
        )

        if not alternatives:
            logger.info("No type-matched alternatives. Searching across all types...")
            alternatives = self.find_similar_clauses(
                query_text=clause_content,
                clause_type=None,
                top_k=2,
            )

        # Generate comparison notes
        comparison_notes = self._generate_comparison_notes(
            contract_clause=contract_clause,
            alternatives=alternatives,
        )

        return {
            "clause_id": clause_id,
            "fair_alternatives": alternatives,
            "comparison_notes": comparison_notes,
        }

    def _generate_comparison_notes(
        self,
        contract_clause: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
    ) -> str:
        """
        Generate human-readable comparison notes between the contract clause
        and the retrieved fair alternatives.

        Uses keyword heuristics rather than another LLM call (keeps it fast & free).
        """
        if not alternatives:
            return "No fair clause alternatives found in the library for comparison."

        cont = contract_clause.get("content", "").lower()
        ctype = contract_clause.get("type", "general")

        notes_parts: List[str] = []

        # ── Check for common red flags ──────────────────────────
        flags = {
            "termination": [
                ("at any time, for any reason", "Allows termination without cause — fair clauses typically require material breach or reasonable notice."),
                ("15 days", "15-day notice period is very short — fair clauses typically specify 30-60 days."),
                ("immediately", "Immediate termination provision found — may not allow adequate cure period."),
            ],
            "payment": [
                ("1.5%", "1.5% monthly interest is high (~18% APR) — fair clauses typically cap at 1% or applicable legal maximum."),
                ("45 days", "45-day grace period before interest accrues is short — fair clauses offer 30-45 days FROM invoice receipt."),
            ],
            "liability": [
                ("never exceed", "Liability cap may be one-sided — fair clauses apply mutual caps tied to contract value."),
                ("in no event", "Absolute liability disclaimer — fair clauses carve out gross negligence and willful misconduct."),
            ],
            "intellectual_property": [
                ("owned exclusively", "Exclusive ownership without licensing back pre-existing IP — may be overreaching."),
                ("hereby assigns", "Blanket IP assignment — fair clauses typically clarify pre-existing vs. created IP."),
            ],
        }

        type_specific = flags.get(ctype, [])
        for keyword, note in type_specific:
            if keyword in cont:
                notes_parts.append(f"• {note}")

        # ── General notes about alternatives ─────────────────────
        note = f"Found {len(alternatives)} fair clause alternative(s) "
        note += f"with similarity scores: "
        note += ", ".join(
            f"{a['title'][:40]} ({a['score']:.2f})" for a in alternatives
        )
        note += ". "
        if alternatives and alternatives[0]["score"] > 0.8:
            note += "High similarity — the contract clause is close to fair-market language."
        elif alternatives and alternatives[0]["score"] > 0.5:
            note += "Moderate similarity — some deviations from fair-market language detected."
        else:
            note += "Low similarity — the contract clause differs significantly from fair-market standards."

        if notes_parts:
            note += "\n\n⚠️ Specific concerns:\n" + "\n".join(notes_parts)
        else:
            note += "\n\nNo specific red flags detected via keyword analysis."

        return note

    # ── Health Check ────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """
        Verify Qdrant connectivity and collection status.

        Returns:
            Dict with status info.
        """
        try:
            collections = self.qdrant.get_collections()
            names = [c.name for c in collections.collections]
            has_collection = COLLECTION_NAME in names
            count = 0
            if has_collection:
                info = self.qdrant.get_collection(COLLECTION_NAME)
                count = info.points_count

            return {
                "qdrant_status": "connected",
                "collection_exists": has_collection,
                "clause_count": count,
                "qdrant_host": f"{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
            }
        except Exception as exc:
            return {
                "qdrant_status": "disconnected",
                "error": str(exc),
            }


# Module-level singleton
rag_service = RAGService()
