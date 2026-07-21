#!/usr/bin/env bash
# ── ContractGuard Startup Script ─────────────────────────────────
# 1. Waits for Qdrant (if remote mode)
# 2. Starts uvicorn immediately so Render detects the open port
# 3. Auto-seeding happens in the FastAPI lifespan handler (main.py)
set -e

PORT="${PORT:-8000}"
APP_HOST="${APP_HOST:-0.0.0.0}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           ContractGuard API — Starting Up                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  QDRANT_HOST: ${QDRANT_HOST:-localhost}"
echo "  QDRANT_PORT: ${QDRANT_PORT:-6333}"
echo "  QDRANT_MODE: ${QDRANT_MODE:-local}"
echo "  APP_PORT:    ${PORT}"
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
            echo "[startup] WARNING: Qdrant not reachable. Continuing anyway..."
        fi
        sleep 2
    done
fi

echo "[startup] Starting uvicorn on ${APP_HOST}:${PORT}..."
echo "[startup] (Database seeding will happen on first HTTP request via lifespan handler)"
echo ""

# ── Start uvicorn ───────────────────────────────────────────────
exec uvicorn main:app \
    --host "${APP_HOST}" \
    --port "${PORT}" \
    --log-level "${LOG_LEVEL:-info}" \
    --forwarded-allow-ips "*" \
    --proxy-headers
