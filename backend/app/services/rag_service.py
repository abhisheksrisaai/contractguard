"""
ContractGuard - RAG Service (Retrieval-Augmented Generation)

Handles:
- Vector embeddings via sentence-transformers (or persisted TF-IDF fallback)
- Storage & retrieval in Qdrant vector DB
- Finding similar fair clauses for contract clause comparison
"""

import json
import logging
import os
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
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
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 / TF-IDF target dim
TFIDF_MAX_FEATURES = 384  # max features for TF-IDF (matches VECTOR_SIZE)
EMBEDDING_VERSION = "tfidf-v2"  # bump to force reseed on embedding change


class RAGService:
    """
    Retrieval-Augmented Generation service for fair contract clauses.

    Uses:
    - Qdrant for vector storage & similarity search
    - sentence-transformers/all-MiniLM-L6-v2 for embeddings (if cached)
    - Persisted TF-IDF vectorizer (fitted on entire clause library) as fallback
    """

    def __init__(self) -> None:
        self._qdrant: Optional[QdrantClient] = None
        self._encoder: Optional[SentenceTransformer] = None
        self._vectorizer: Any = None  # TfidfVectorizer (loaded lazily)

    # ── Qdrant Client ────────────────────────────────────────────────

    @property
    def qdrant(self) -> QdrantClient:
        """Lazy-initialize Qdrant client (remote or local mode)."""
        if self._qdrant is None:
            if settings.QDRANT_MODE == "local":
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

    # ── Qdrant data dir path ─────────────────────────────────────────

    def _qdrant_data_dir(self) -> Path:
        """Return the path to the Qdrant local data directory."""
        local_path = settings.QDRANT_LOCAL_PATH
        if not local_path:
            local_path = str(settings.project_root / "qdrant_data")
        return Path(local_path)

    # ── Embedding version marker ─────────────────────────────────────

    @staticmethod
    def embedding_version_path() -> Path:
        """Path to the embedding version marker file."""
        local_path = settings.QDRANT_LOCAL_PATH
        if not local_path:
            local_path = str(settings.project_root / "qdrant_data")
        return Path(local_path) / "embedding_version.txt"

    @classmethod
    def get_persisted_version(cls) -> Optional[str]:
        """Read the persisted embedding version, or None."""
        path = cls.embedding_version_path()
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return None

    @classmethod
    def write_version_marker(cls) -> None:
        """Write the current embedding version marker."""
        path = cls.embedding_version_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(EMBEDDING_VERSION, encoding="utf-8")

    @classmethod
    def embedding_needs_reseed(cls) -> bool:
        """True if the embedding version has changed since last seed."""
        current = cls.get_persisted_version()
        return current != EMBEDDING_VERSION

    # ── Sentence-Transformer Encoder ──────────────────────────────────

    @property
    def encoder(self):
        """Lazy-load the sentence-transformer embedding model.
        Returns None if model fails to load, triggering TF-IDF fallback."""
        if self._encoder is None:
            if not HAS_SENTENCE_TRANSFORMERS:
                logger.info("sentence-transformers not installed. Using TF-IDF fallback.")
                self._encoder = None
                return None

            model_name = settings.EMBEDDING_MODEL.replace("sentence-transformers/", "")
            logger.info("Loading embedding model: %s ...", model_name)

            cache_root = os.path.expanduser("~/.cache/huggingface/hub")
            model_blobs = os.path.join(
                cache_root, "models--sentence-transformers--all-MiniLM-L6-v2", "blobs"
            )
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

    # ── Persisted TF-IDF Vectorizer ───────────────────────────────────

    def _vectorizer_path(self) -> Path:
        """Path to the persisted TF-IDF vectorizer file."""
        return self._qdrant_data_dir() / "tfidf_vectorizer.joblib"

    def _load_clause_corpus(self) -> List[str]:
        """Load all clause texts from fair_clauses.json for fitting the vectorizer."""
        clauses_path = (
            Path(__file__).resolve().parent.parent.parent
            / "clause_library" / "fair_clauses.json"
        )
        if not clauses_path.exists():
            raise FileNotFoundError(
                f"Fair clauses file not found: {clauses_path}"
            )
        with open(clauses_path, "r", encoding="utf-8") as f:
            clauses = json.load(f)

        corpus = []
        for c in clauses:
            title = c.get("title", "")
            content = c.get("content", "")
            corpus.append(f"{title}\n{content}")
        return corpus

    def _get_or_create_vectorizer(self):
        """Load persisted TF-IDF vectorizer, or fit+persist a new one
        on the full clause library corpus."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        import joblib

        v_path = self._vectorizer_path()

        # Try loading persisted vectorizer
        if v_path.exists():
            try:
                self._vectorizer = joblib.load(str(v_path))
                logger.info(
                    "Loaded persisted TF-IDF vectorizer from %s (%d features)",
                    v_path.name, len(self._vectorizer.get_feature_names_out()),
                )
                return
            except Exception as exc:
                logger.warning(
                    "Failed to load persisted vectorizer: %s. Re-fitting.", exc
                )

        # Fit on full clause library
        logger.info("Fitting TF-IDF vectorizer on clause library corpus...")
        corpus = self._load_clause_corpus()
        logger.info("  Corpus: %d documents", len(corpus))

        self._vectorizer = TfidfVectorizer(
            max_features=TFIDF_MAX_FEATURES,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )
        self._vectorizer.fit(corpus)
        logger.info(
            "  Fitted: %d features", len(self._vectorizer.get_feature_names_out())
        )

        # Persist to disk
        v_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._vectorizer, str(v_path))
        logger.info("  Persisted to %s", v_path.name)

    # ── Embedding Generation ─────────────────────────────────────────

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a vector embedding for a text string.

        Uses sentence-transformer model if available; falls back to
        persisted TF-IDF vectorizer.

        Args:
            text: Input text to embed.

        Returns:
            List of floats (384-dim).
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
            logger.warning("Sentence-transformer encode failed: %s. Using TF-IDF fallback.", exc)

        return self._fallback_embedding(truncated)

    def _fallback_embedding(self, text: str) -> List[float]:
        """
        Embed a single text using the persisted TF-IDF vectorizer.

        The vectorizer is fitted once on the entire clause library and
        persisted to disk.  Every call to this method uses the SAME
        feature space, so cosine similarity between vectors is meaningful.

        Steps:
        1. Ensure vectorizer is loaded (fits on clause library if missing)
        2. transform(text) → dense array
        3. L2-normalize
        4. Pad or truncate to exactly VECTOR_SIZE (384) dims
        """
        import joblib

        if self._vectorizer is None:
            self._get_or_create_vectorizer()

        # Transform: 1-row sparse → dense
        vec = self._vectorizer.transform([text]).toarray()[0]  # shape: (n_features,)

        # L2-normalize
        norm = math.sqrt(float((vec * vec).sum()))
        if norm > 0:
            vec = vec / norm

        result = vec.tolist()

        # Pad or truncate to exactly VECTOR_SIZE
        if len(result) < VECTOR_SIZE:
            result += [0.0] * (VECTOR_SIZE - len(result))
        else:
            result = result[:VECTOR_SIZE]

        # Re-normalize after padding (shouldn't change anything since
        # padded values are zero, but just to be safe)
        mag = math.sqrt(sum(v * v for v in result))
        if mag > 0 and abs(mag - 1.0) > 1e-6:
            result = [v / mag for v in result]

        return result

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
        """Retrieve a clause by its ID."""
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
        """Retrieve all fair clauses from the collection."""
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
        """Delete all points from the collection."""
        try:
            info = self.qdrant.get_collection(COLLECTION_NAME)
            count = info.points_count if info else 0
            self.qdrant.delete(
                collection_name=COLLECTION_NAME,
                points_selector=Filter(),
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

        query_filter = None
        if clause_type:
            query_filter = Filter(
                must=[FieldCondition(key="type", match=MatchValue(value=clause_type))]
            )

        try:
            results = self.qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                limit=min(top_k, 50),
                query_filter=query_filter,
                with_payload=True,
            )
        except AttributeError:
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
        clause_content = contract_clause.get("content", "")
        clause_type = contract_clause.get("type", "general")

        logger.info("Comparing clause %s (type=%s)...", clause_id, clause_type)

        if not clause_content.strip():
            return {
                "clause_id": clause_id,
                "fair_alternatives": [],
                "comparison_notes": "Empty clause — nothing to compare.",
            }

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
        and the retrieved fair alternatives, using keyword heuristics.
        """
        if not alternatives:
            return "No fair clause alternatives found in the library for comparison."

        cont = contract_clause.get("content", "").lower()
        ctype = contract_clause.get("type", "general")

        notes_parts: List[str] = []

        # ── Check for common red flags ──────────────────────────
        flags: Dict[str, List[tuple]] = {
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
            "employment_notice": [
                ("7 days", "7-day notice period is very short — fair employment clauses specify 30 days."),
                ("15 days", "15-day notice period is short for employment — 30 days is the fair standard."),
                ("deduct", "Salary deduction for insufficient notice is a red flag — fair clauses provide pay in lieu instead."),
            ],
            "employment_termination": [
                ("immediate", "Immediate termination without warning or cure period is a red flag."),
                ("at will", "At-will termination without cause or notice may violate fair employment standards."),
                ("no notice", "Termination with no notice period is a significant risk."),
            ],
            "employment_gratuity": [
                ("subject to", "Gratuity conditioned on client payment is unfair — gratuity is a statutory right."),
                ("client", "Gratuity tied to client payments is a violation of statutory rights."),
                ("discretion", "Gratuity at employer discretion may circumvent statutory obligations."),
            ],
            "employment_salary": [
                ("10th", "Salary paid after the 7th of the month is a red flag — fair standard is by the 7th."),
                ("15th", "Salary paid on the 15th is late — fair standard is by the 7th."),
                ("deduction", "Unauthorized salary deductions are a red flag — only statutory deductions are permitted."),
            ],
            "employment_noncompete": [
                ("2 year", "2+ year non-compete is likely unenforceable — fair clauses limit to 6-12 months."),
                ("3 year", "3+ year non-compete is excessive — fair clauses limit to 6-12 months."),
                ("anywhere", "Worldwide/geographically unlimited non-compete is likely unenforceable."),
                ("compensation", "No compensation during non-compete period is a red flag — fair clauses pay 50% salary."),
            ],
            "employment_confidentiality": [
                ("perpetual", "Perpetual confidentiality is overly broad — fair clauses limit to 2 years post-employment."),
                ("5 year", "5+ year confidentiality may be excessive — 2 years is standard post-employment."),
            ],
            "employment_ip": [
                ("all inventions", "Blanket assignment of ALL inventions (even off-hours) is overreaching."),
                ("hereby assigns", "Blanket IP assignment without excluding pre-existing IP is a red flag."),
            ],
            "employment_indemnity": [
                ("unlimited", "Unlimited employee indemnity is a major red flag — fair clauses cap at 3 months salary."),
                ("hold harmless", "One-sided hold harmless from employee is unfair — should be mutual."),
            ],
            "employment_hours": [
                ("48 hours", "48-hour workweek at maximum — fair clauses provide overtime pay at 2x rate."),
                ("overtime", "Mandatory overtime is a red flag — overtime should be voluntary."),
                ("no overtime", "No overtime pay provision — fair clauses guarantee 2x rate for overtime."),
            ],
            "employment_transfer": [
                ("any location", "Unrestricted transfer power is a red flag — fair clauses limit by geography and provide allowance."),
                ("refuse", "No right to refuse transfer — fair clauses allow refusal on valid grounds."),
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
        # Recalibrated thresholds for TF-IDF-v2 cosine space
        if alternatives and alternatives[0]["score"] > 0.55:
            note += "High similarity — the contract clause is close to fair-market language."
        elif alternatives and alternatives[0]["score"] > 0.25:
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
