"""Portfolio valuation and trade execution logic.

This module owns all trade math and P&L computation. The DB layer
(`app.db`) provides raw persistence primitives only; everything here
composes them into correct buy/sell semantics and portfolio totals.

All functions take an explicit ``conn`` (a ``sqlite3.Connection``) and a
``cache`` (an ``app.market.PriceCache``) so they are trivially testable and
reusable by the LLM layer without any HTTP context.
"""

from __future__ import annotations

import sqlite3

from app.db import (
    DEFAULT_USER_ID,
    delete_position,
    get_cash_balance,
    get_position,
    get_positions,
    record_snapshot,
    record_trade,
    set_cash_balance,
    upsert_position,
)
from app.market import PriceCache

#: Quantities at or below this magnitude are treated as a fully-closed position.
_ZERO_QTY_EPSILON = 1e-9


def build_portfolio(
    conn: sqlite3.Connection,
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Compute the full portfolio snapshot using current cache prices.

    Returns a dict with:
        cash_balance, positions_value, total_value, unrealized_pnl,
        positions: [{ticker, quantity, avg_cost, current_price,
                     market_value, unrealized_pnl, change_percent}]

    ``current_price`` is taken from the price cache; when no price has been
    seen yet for a ticker it falls back to ``avg_cost`` (so an untracked
    position still contributes its cost basis rather than vanishing).
    """
    cash_balance = get_cash_balance(conn, user_id)
    positions_value = 0.0
    unrealized_pnl_total = 0.0
    out_positions: list[dict] = []

    for pos in get_positions(conn, user_id):
        ticker = pos["ticker"]
        quantity = float(pos["quantity"])
        avg_cost = float(pos["avg_cost"])

        cached = cache.get_price(ticker)
        current_price = float(cached) if cached is not None else avg_cost

        market_value = quantity * current_price
        unrealized_pnl = (current_price - avg_cost) * quantity
        change_percent = (
            ((current_price - avg_cost) / avg_cost * 100.0) if avg_cost != 0 else 0.0
        )

        positions_value += market_value
        unrealized_pnl_total += unrealized_pnl

        out_positions.append(
            {
                "ticker": ticker,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "change_percent": change_percent,
            }
        )

    total_value = cash_balance + positions_value

    return {
        "cash_balance": cash_balance,
        "positions_value": positions_value,
        "total_value": total_value,
        "unrealized_pnl": unrealized_pnl_total,
        "positions": out_positions,
    }


def record_portfolio_snapshot(
    conn: sqlite3.Connection,
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Compute current total value and persist a portfolio snapshot."""
    portfolio = build_portfolio(conn, cache, user_id)
    return record_snapshot(conn, portfolio["total_value"], user_id)


def execute_trade(
    conn: sqlite3.Connection,
    cache: PriceCache,
    ticker: str,
    side: str,
    quantity: float,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Execute a market order at the current cache price.

    Validates inputs, updates cash + position, records the trade, then
    records a portfolio snapshot. Returns the recorded trade dict
    ``{id, user_id, ticker, side, quantity, price, executed_at}``.

    Raises:
        ValueError: On any validation failure (the API layer maps these to
            HTTP 400). Messages are user-facing.
    """
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise ValueError("Ticker must be a non-empty string")

    side = (side or "").strip().lower()
    if side not in ("buy", "sell"):
        raise ValueError("Side must be 'buy' or 'sell'")

    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValueError("Quantity must be a number") from None
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0")

    price = cache.get_price(ticker)
    if price is None:
        raise ValueError(f"No price available for {ticker}")
    price = float(price)

    existing = get_position(conn, ticker, user_id)
    cash = get_cash_balance(conn, user_id)

    if side == "buy":
        cost = quantity * price
        if cash < cost:
            raise ValueError(
                f"Insufficient cash to buy {quantity} {ticker} "
                f"(need ${cost:,.2f}, have ${cash:,.2f})"
            )
        old_qty = float(existing["quantity"]) if existing else 0.0
        old_avg = float(existing["avg_cost"]) if existing else 0.0
        new_qty = old_qty + quantity
        new_avg = (old_qty * old_avg + quantity * price) / new_qty
        set_cash_balance(conn, cash - cost, user_id)
        upsert_position(conn, ticker, new_qty, new_avg, user_id)
    else:  # sell
        if existing is None:
            raise ValueError(f"No position in {ticker} to sell")
        old_qty = float(existing["quantity"])
        if old_qty < quantity:
            raise ValueError(
                f"Insufficient shares to sell {quantity} {ticker} "
                f"(have {old_qty})"
            )
        proceeds = quantity * price
        new_qty = old_qty - quantity
        set_cash_balance(conn, cash + proceeds, user_id)
        if new_qty <= _ZERO_QTY_EPSILON:
            delete_position(conn, ticker, user_id)
        else:
            upsert_position(conn, ticker, new_qty, float(existing["avg_cost"]), user_id)

    trade = record_trade(conn, ticker, side, quantity, price, user_id)

    # Snapshot the portfolio immediately after a successful trade.
    record_portfolio_snapshot(conn, cache, user_id)

    return trade
