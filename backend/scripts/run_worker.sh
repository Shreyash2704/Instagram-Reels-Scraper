#!/usr/bin/env bash
# From repo: backend/scripts/run_worker.sh — RQ worker for "pipeline" queue.
set -euo pipefail
BACKEND_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BACKEND_ROOT"
export PYTHONPATH="${PYTHONPATH:-$BACKEND_ROOT}"
REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
QUEUE_NAME="${RQ_QUEUE_NAME:-pipeline}"
echo "RQ worker using ${REDIS_URL} queue ${QUEUE_NAME}"
exec rq worker -u "$REDIS_URL" "$QUEUE_NAME"
