#!/usr/bin/env bash
# ── ContractGuard Startup Script ─────────────────────────────────
# Runs on Render deployment:
#   1. Checks if Qdrant collection exists and is seeded
#   2. Runs seed_db.py if collection is empty
#   3. Starts uvicorn
#
# Ensures fair clause library is always available on first deploy
# while persisting data across subsequent deploys via Render disk.

set -e

PORT="${PORT:-8000}"
APP_HOST="${APP_HOST:-0.0.0.0}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           ContractGuard API — Starting Up                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  QDRANT_HOST: ${QDRANT_HOST:-localhost}"
echo "  QDRANT_PORT: ${QDRANT_PORT:-6333}"
echo "  QDRANT_MODE: ${QDRANT_MODE:-local}"
echo "  APP_PORT:    ${PORT}"
echo "  APP_DEBUG:   ${APP_DEBUG:-false}"
echo ""

# ── Wait for Qdrant if remote ───────────────────────────────────
if [ "${QDRANT_MODE}" = "remote" ]; then
    echo "[startup] Waiting for Qdrant at ${QDRANT_HOST}:${QDRANT_PORT}..."
    for i in $(seq 1 30); do
        if curl -s -o /dev/null "http://${QDRANT_HOST}:${QDRANT_PORT}/collections" 2>/dev/null; then
            echo "[startup] Qdrant is ready!"
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo "[startup] WARNING: Qdrant not reachable after 30 attempts. Continuing anyway..."
        fi
        sleep 2
    done
fi

# ── Check if collection needs seeding ───────────────────────────
echo "[startup] Checking if Qdrant fair_clauses collection exists..."

# Use Python to check and optionally seed
python -c "
import os, sys
sys.path.insert(0, '/app')

from app.core.config import settings
from app.services.rag_service import RAGService, COLLECTION_NAME

try:
    rag = RAGService()
    health = rag.health_check()
    count = health.get('clause_count', 0)
    exists = health.get('collection_exists', False)

    if not exists:
        print(f'[startup] Collection {COLLECTION_NAME} does not exist. Seeding...')
        sys.exit(2)   # exit code 2 = needs seed
    elif count == 0:
        print(f'[startup] Collection {COLLECTION_NAME} exists but is empty. Seeding...')
        sys.exit(2)   # exit code 2 = needs seed
    else:
        print(f'[startup] Collection {COLLECTION_NAME} has {count} clauses. Skipping seed.')
        sys.exit(0)   # exit code 0 = already seeded
except Exception as e:
    print(f'[startup] Error checking collection: {e}. Will attempt seed.')
    sys.exit(2)
"

SEED_EXIT_CODE=$?

if [ $SEED_EXIT_CODE -eq 2 ]; then
    echo "[startup] Running seed_db.py..."
    python /app/seed_db.py
    if [ $? -ne 0 ]; then
        echo "[startup] WARNING: seed_db.py failed. API will start but RAG may not work."
    else
        echo "[startup] Seed completed successfully!"
    fi
else
    echo "[startup] Database already seeded. Skipping."
fi

echo ""
echo "[startup] Starting uvicorn on ${APP_HOST}:${PORT}..."
echo ""

# ── Start uvicorn ───────────────────────────────────────────────
exec uvicorn main:app \
    --host "${APP_HOST}" \
    --port "${PORT}" \
    --log-level "${LOG_LEVEL:-info}" \
    --forwarded-allow-ips "*" \
    --proxy-headers
