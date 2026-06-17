#!/usr/bin/env bash
# Start the FinAlly container (macOS/Linux). Idempotent.
#
# Usage:
#   ./scripts/start_mac.sh [--build] [--no-open]
#     --build     Force a rebuild of the image even if it already exists.
#     --no-open   Do not attempt to open the browser.
set -euo pipefail

IMAGE="finally:latest"
CONTAINER="finally"
VOLUME="finally-data"
PORT=8000
URL="http://localhost:${PORT}"

# Resolve project root (parent of this scripts/ dir) so paths work from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

BUILD=0
OPEN=1
for arg in "$@"; do
  case "$arg" in
    --build)   BUILD=1 ;;
    --no-open) OPEN=0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed or not on PATH." >&2
  exit 1
fi

# Build the image if it's missing or a rebuild was requested.
if [ "$BUILD" -eq 1 ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Building image ${IMAGE}..."
  docker build -t "$IMAGE" .
else
  echo "Image ${IMAGE} already exists (use --build to rebuild)."
fi

# Ensure a .env exists; fall back to .env.example so --env-file never fails.
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
  if [ -f ".env.example" ]; then
    echo "No .env found; copying .env.example -> .env (edit it to add your keys)."
    cp .env.example .env
  else
    echo "Warning: no .env or .env.example found; starting without an env file." >&2
    ENV_FILE=""
  fi
fi

# If a container with this name exists (running or stopped), remove it first
# so re-running picks up the latest image/config. The volume is untouched.
if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Removing existing container ${CONTAINER}..."
  docker rm -f "$CONTAINER" >/dev/null
fi

echo "Starting container ${CONTAINER}..."
RUN_ARGS=(-d --name "$CONTAINER" -p "${PORT}:8000" -v "${VOLUME}:/app/db")
if [ -n "$ENV_FILE" ]; then
  RUN_ARGS+=(--env-file "$ENV_FILE")
fi
docker run "${RUN_ARGS[@]}" "$IMAGE" >/dev/null

echo ""
echo "FinAlly is starting at: ${URL}"
echo "  Logs:  docker logs -f ${CONTAINER}"
echo "  Stop:  ./scripts/stop_mac.sh"

if [ "$OPEN" -eq 1 ]; then
  if command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
  fi
fi
