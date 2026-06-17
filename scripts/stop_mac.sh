#!/usr/bin/env bash
# Stop and remove the FinAlly container (macOS/Linux). Idempotent.
# Does NOT remove the named volume, so the SQLite database persists.
#
# Usage: ./scripts/stop_mac.sh
set -euo pipefail

CONTAINER="finally"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed or not on PATH." >&2
  exit 1
fi

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Stopping and removing container ${CONTAINER}..."
  docker rm -f "$CONTAINER" >/dev/null
  echo "Done. The 'finally-data' volume was preserved (your data is safe)."
else
  echo "Container ${CONTAINER} is not present; nothing to stop."
fi
