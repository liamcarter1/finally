"""Health-check endpoint used by Docker healthchecks."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health() -> dict:
    """Liveness/readiness probe. Returns HTTP 200 when the app is up."""
    return {"status": "ok"}
