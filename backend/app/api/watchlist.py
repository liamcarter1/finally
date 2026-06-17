"""Watchlist API routes."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_cache, get_conn, get_source
from app.market import MarketDataSource, PriceCache
from app.schemas import WatchlistRequest
from app.services import (
    add_to_watchlist,
    get_watchlist_with_prices,
    remove_from_watchlist,
)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
async def get_watchlist(
    conn: sqlite3.Connection = Depends(get_conn),
    cache: PriceCache = Depends(get_cache),
) -> dict:
    """Return the watchlist with latest prices."""
    return {"watchlist": get_watchlist_with_prices(conn, cache)}


@router.post("")
async def post_watchlist(
    body: WatchlistRequest,
    conn: sqlite3.Connection = Depends(get_conn),
    cache: PriceCache = Depends(get_cache),
    source: MarketDataSource = Depends(get_source),
) -> dict:
    """Add a ticker to the watchlist and return the updated list."""
    try:
        watchlist = await add_to_watchlist(conn, source, cache, body.ticker)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"watchlist": watchlist}


@router.delete("/{ticker}")
async def delete_watchlist(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_conn),
    cache: PriceCache = Depends(get_cache),
    source: MarketDataSource = Depends(get_source),
) -> dict:
    """Remove a ticker from the watchlist and return the updated list."""
    try:
        watchlist = await remove_from_watchlist(conn, source, cache, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"watchlist": watchlist}
