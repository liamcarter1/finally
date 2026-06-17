"""Portfolio API routes."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_cache, get_conn
from app.db import list_snapshots
from app.market import PriceCache
from app.schemas import TradeRequest
from app.services import build_portfolio, execute_trade

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio(
    conn: sqlite3.Connection = Depends(get_conn),
    cache: PriceCache = Depends(get_cache),
) -> dict:
    """Return the current portfolio (cash, positions, totals, P&L)."""
    return build_portfolio(conn, cache)


@router.post("/trade")
async def post_trade(
    body: TradeRequest,
    conn: sqlite3.Connection = Depends(get_conn),
    cache: PriceCache = Depends(get_cache),
) -> dict:
    """Execute a market order and return the trade plus the updated portfolio."""
    try:
        trade = execute_trade(conn, cache, body.ticker, body.side, body.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"trade": trade, "portfolio": build_portfolio(conn, cache)}


@router.get("/history")
async def get_history(conn: sqlite3.Connection = Depends(get_conn)) -> dict:
    """Return portfolio value snapshots over time (oldest first)."""
    snapshots = [
        {"total_value": s["total_value"], "recorded_at": s["recorded_at"]}
        for s in list_snapshots(conn)
    ]
    return {"snapshots": snapshots}
