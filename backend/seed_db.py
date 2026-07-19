#!/usr/bin/env python3
"""
ContractGuard - Seed Fair Clauses into Qdrant Vector Database

Loads fair_clauses.json and adds all clauses to the Qdrant collection.
Run once after starting Qdrant: docker run -p 6333:6333 qdrant/qdrant
"""

import json
import logging
import sys
from pathlib import Path

# Ensure backend/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.config import settings
from app.services.rag_service import RAGService, COLLECTION_NAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_db")

FAIR_CLAUSES_PATH = Path(__file__).resolve().parent / "clause_library" / "fair_clauses.json"


def load_fair_clauses() -> list:
    """Load fair clauses from JSON file."""
    if not FAIR_CLAUSES_PATH.exists():
        raise FileNotFoundError(f"Fair clauses file not found: {FAIR_CLAUSES_PATH}")

    with open(FAIR_CLAUSES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("fair_clauses.json must contain a non-empty list of clause objects.")

    logger.info("Loaded %d fair clauses from %s", len(data), FAIR_CLAUSES_PATH.name)
    return data


def main() -> None:
    """Seed the Qdrant collection with fair clauses."""
    logger.info("=" * 60)
    logger.info("ContractGuard - Seeding Fair Clause Library")
    logger.info("=" * 60)

    # Validate Groq not needed here, but Qdrant must be up
    logger.info("Qdrant: %s:%s", settings.QDRANT_HOST, settings.QDRANT_PORT)
    logger.info("Embedding model: %s", settings.EMBEDDING_MODEL)

    try:
        rag = RAGService()
    except ConnectionError as exc:
        logger.error("Cannot proceed: %s", exc)
        logger.error("Start Qdrant first: docker run -d -p 6333:6333 qdrant/qdrant")
        sys.exit(1)
    except Exception as exc:
        logger.error("Failed to initialize RAGService: %s", exc)
        sys.exit(1)

    # Load clauses
    try:
        clauses = load_fair_clauses()
    except Exception as exc:
        logger.error("Failed to load fair clauses: %s", exc)
        sys.exit(1)

    # Create collection (force recreate for clean seed)
    logger.info("Creating/recreating collection '%s'...", COLLECTION_NAME)
    rag.create_collection(force_recreate=True)

    # Add all clauses
    added = 0
    failed = 0

    for i, clause in enumerate(clauses, start=1):
        clause_type = clause.get("type", "general")
        title = clause.get("title", f"Clause {i}")
        content = clause.get("content", "")

        if not content.strip():
            logger.warning("Skipping clause %d ('%s'): empty content.", i, title)
            failed += 1
            continue

        try:
            cid = rag.add_fair_clause(
                clause_type=clause_type,
                title=title,
                content=content,
            )
            added += 1
            print(f"  ✅ [{added:2d}] {title[:70]} (type: {clause_type}, id: {cid[:8]}...)")
        except Exception as exc:
            failed += 1
            logger.error("  ❌ Failed to add '%s': %s", title[:60], exc)

    # Summary
    print()
    logger.info("=" * 60)
    logger.info("SEEDING COMPLETE")
    logger.info("  Added:    %d", added)
    logger.info("  Failed:   %d", failed)
    logger.info("  Total:    %d clauses in library", len(clauses))

    # Verify
    health = rag.health_check()
    logger.info("  Qdrant:   %s | Collection: %s | Points: %d",
                health.get("qdrant_status"),
                "exists" if health.get("collection_exists") else "missing",
                health.get("clause_count", 0))

    if failed > 0:
        logger.warning("Some clauses failed to seed. Check errors above.")
        sys.exit(1)

    logger.info("✅ Fair clause library is ready for use!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
