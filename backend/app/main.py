"""FastAPI application entrypoint for FinAlly.

Exposes a module-level ``app`` so the ASGI server runs ``app.main:app``.

Responsibilities:
    * App lifecycle (DB connection, price cache, market data source, and a
      30s portfolio-snapshot background task) via a lifespan context manager.
    * Mounting the SSE router, the REST API routers, and the static frontend.

The static frontend is served from ``STATIC_DIR`` (set to ``/app/static`` in
the container). For local dev it falls back to ``../frontend/out`` and is
skipped gracefully if absent.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import health_router, portfolio_router, watchlist_router
from app.db import close_default_connection, get_default_connection, list_watchlist
from app.llm import router as chat_router
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.services import record_portfolio_snapshot

logger = logging.getLogger(__name__)

#: How often the background task records a portfolio snapshot.
SNAPSHOT_INTERVAL_SECONDS = 30.0

#: The single shared price cache. Created at import time so the SSE router can
#: bind to it, and reused (not replaced) by the lifespan so the data source
#: writes into the same object the stream reads from.
_price_cache = PriceCache()


def _resolve_static_dir() -> Path | None:
    """Resolve the static frontend directory, or ``None`` if unavailable.

    Uses ``STATIC_DIR`` when set, otherwise falls back to the Next.js export
    at ``<backend>/../frontend/out``. Returns ``None`` (with a warning) if the
    resolved directory does not exist.
    """
    env_dir = os.environ.get("STATIC_DIR")
    if env_dir:
        candidate = Path(env_dir)
    else:
        # app/main.py -> app -> backend -> project root -> frontend/out
        candidate = Path(__file__).resolve().parents[2] / "frontend" / "out"

    if candidate.is_dir():
        return candidate
    logger.warning("Static directory %s not found; skipping static file mounting", candidate)
    return None


async def _snapshot_loop(app: FastAPI) -> None:
    """Record a portfolio snapshot every ``SNAPSHOT_INTERVAL_SECONDS``."""
    conn = app.state.db_conn
    cache = app.state.price_cache
    while True:
        try:
            await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)
            record_portfolio_snapshot(conn, cache)
        except asyncio.CancelledError:
            break
        except Exception:  # pragma: no cover - defensive; keep the loop alive
            logger.exception("Failed to record portfolio snapshot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup/shutdown of shared resources."""
    conn = get_default_connection()
    cache = _price_cache
    source = create_market_data_source(cache)

    tickers = list_watchlist(conn)
    await source.start(tickers)

    app.state.db_conn = conn
    app.state.price_cache = cache
    app.state.market_source = source
    app.state.snapshot_task = asyncio.create_task(_snapshot_loop(app))

    logger.info("FinAlly backend started with %d tickers", len(tickers))
    try:
        yield
    finally:
        task: asyncio.Task = app.state.snapshot_task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await source.stop()
        close_default_connection()
        logger.info("FinAlly backend shut down")


app = FastAPI(title="FinAlly", version="0.1.0", lifespan=lifespan)

# REST API routers first so /api/* always wins over the static catch-all.
app.include_router(health_router)
app.include_router(portfolio_router)
app.include_router(watchlist_router)
app.include_router(chat_router)

# SSE streaming router (GET /api/stream/prices), bound to the shared cache.
app.include_router(create_stream_router(_price_cache))


def _mount_static(app: FastAPI) -> None:
    """Mount the static frontend with an SPA fallback to index.html.

    API routes are registered above and take precedence. A catch-all route
    serves ``index.html`` for any non-``/api`` path that does not map to a
    real static file (client-side routing support).
    """
    static_dir = _resolve_static_dir()
    if static_dir is None:
        return

    index_file = static_dir / "index.html"

    # Serve real static assets (JS/CSS/_next/etc.) under their own paths.
    next_dir = static_dir / "_next"
    if next_dir.is_dir():
        app.mount("/_next", StaticFiles(directory=next_dir), name="next-assets")

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str, request: Request):
        # Never shadow the API; let FastAPI return its own 404 for /api/*.
        if full_path.startswith("api/") or full_path == "api":
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        candidate = static_dir / full_path
        if candidate.is_file():
            return FileResponse(candidate)

        # Try the Next.js exported HTML for this route (e.g. about/index.html).
        html_candidate = static_dir / full_path / "index.html"
        if html_candidate.is_file():
            return FileResponse(html_candidate)

        # SPA fallback.
        if index_file.is_file():
            return FileResponse(index_file)
        return JSONResponse({"detail": "Not Found"}, status_code=404)


_mount_static(app)
