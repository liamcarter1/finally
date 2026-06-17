# syntax=docker/dockerfile:1

# =============================================================================
# FinAlly — multi-stage build
#   Stage 1: build the Next.js static export (frontend/out)
#   Stage 2: uv-managed FastAPI app serving /api/* + the static export on :8000
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Frontend build (Next.js static export -> /frontend/out)
# -----------------------------------------------------------------------------
FROM node:20-slim AS frontend

WORKDIR /frontend

# Copy manifests first for better layer caching. The glob keeps the build
# working whether or not a lockfile is present.
COPY frontend/package.json frontend/package-lock.json* frontend/npm-shrinkwrap.json* ./

# Prefer the reproducible `npm ci` (needs a lockfile); fall back to `npm install`.
RUN if [ -f package-lock.json ] || [ -f npm-shrinkwrap.json ]; then \
        npm ci; \
    else \
        npm install; \
    fi

# Copy the rest of the frontend source and produce the static export.
COPY frontend/ ./

# `next build` with `output: 'export'` writes the static site to /frontend/out.
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Backend runtime (uv + FastAPI + uvicorn)
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS backend

# uv: install via pip into the system environment (small, no extra installer step).
RUN pip install --no-cache-dir uv

# Keep uv predictable inside the image:
#   - copy packages into the project venv (no hardlink warnings across layers)
#   - don't have uv manage Python downloads; use the image's interpreter
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy dependency manifests first so `uv sync` is cached unless they change.
COPY backend/pyproject.toml backend/uv.lock* ./

# Install dependencies from the frozen lockfile when present; otherwise resolve.
# --no-install-project: project code isn't copied yet, so only deps are installed here.
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --no-install-project --extra dev || uv sync --no-install-project --extra dev; \
    else \
        uv sync --no-install-project --extra dev; \
    fi

# Copy the backend application source.
COPY backend/ ./

# Install the project itself now that the source is present.
RUN if [ -f uv.lock ]; then \
        uv sync --frozen --extra dev || uv sync --extra dev; \
    else \
        uv sync --extra dev; \
    fi

# Bring the built frontend in as the static dir the backend serves at "/".
# STATIC_DIR (below) points the app here.
COPY --from=frontend /frontend/out ./static

# Runtime defaults (override via --env-file / compose env_file).
#   FINALLY_DB_PATH  -> SQLite location; /app/db is the volume mount target.
#   STATIC_DIR       -> where main.py serves the static export from.
#   LLM_MOCK         -> false by default; E2E sets it true at runtime.
# NOTE: secret-bearing vars (OPENROUTER_API_KEY, MASSIVE_API_KEY) are deliberately
# NOT given ENV defaults here so nothing sensitive is baked into the image; the
# backend treats them as unset/empty (simulator + real-LLM-disabled) when absent.
ENV FINALLY_DB_PATH=/app/db/finally.db \
    STATIC_DIR=/app/static \
    LLM_MOCK=false

# The SQLite directory is volume-mounted; create it so a fresh image works too.
RUN mkdir -p /app/db

EXPOSE 8000

# ASGI entrypoint contract: app.main:app  (see contract notes in README/report).
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
