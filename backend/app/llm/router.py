"""Chat API route: POST /api/chat.

Uses the same dependency-injection pattern as the other routers to obtain the
shared DB connection, price cache, and market-data source from ``app.state``.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_cache, get_conn, get_source
from app.market import MarketDataSource, PriceCache

from .service import chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Body for ``POST /api/chat``."""

    message: str = Field(..., min_length=1, description="The user's chat message")


@router.post("")
async def post_chat(
    body: ChatRequest,
    conn: sqlite3.Connection = Depends(get_conn),
    cache: PriceCache = Depends(get_cache),
    source: MarketDataSource = Depends(get_source),
) -> dict:
    """Process a chat message, auto-execute any actions, and return the result.

    Response shape::

        {
          "message": str,
          "trades": [{ticker, side, quantity, price, status, error?}, ...],
          "watchlist_changes": [{ticker, action, status, error?}, ...],
        }
    """
    return await chat(conn, cache, source, body.message)
