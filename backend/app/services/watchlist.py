"""Watchlist logic: combining persisted tickers with live cache prices and
keeping the market-data source's active ticker set in sync.

The add/remove helpers are async because they drive the market data source
(``await source.add_ticker(...)``). They are callable from both the API layer
and the LLM layer.
"""

from __future__ import annotations

import sqlite3

from app.db import (
    DEFAULT_USER_ID,
    add_watchlist,
    list_watchlist,
    remove_watchlist,
)
from app.market import MarketDataSource, PriceCache


def get_watchlist_with_prices(
    conn: sqlite3.Connection,
    cache: PriceCache,
    user_id: str = DEFAULT_USER_ID,
) -> list[dict]:
    """Return watchlist tickers enriched with their latest cached price.

    Each entry: ``{ticker, price, previous_price, change, change_percent,
    direction}``. Price fields are ``None`` when no tick has arrived yet.
    """
    result: list[dict] = []
    for ticker in list_watchlist(conn, user_id):
        update = cache.get(ticker)
        if update is None:
            result.append(
                {
                    "ticker": ticker,
                    "price": None,
                    "previous_price": None,
                    "change": None,
                    "change_percent": None,
                    "direction": None,
                }
            )
        else:
            result.append(
                {
                    "ticker": ticker,
                    "price": update.price,
                    "previous_price": update.previous_price,
                    "change": update.change,
                    "change_percent": update.change_percent,
                    "direction": update.direction,
                }
            )
    return result


def _normalize(ticker: str) -> str:
    cleaned = (ticker or "").strip().upper()
    if not cleaned:
        raise ValueError("Ticker must be a non-empty string")
    return cleaned


async def add_to_watchlist(
    conn: sqlite3.Connection,
    source: MarketDataSource,
    cache: PriceCache,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> list[dict]:
    """Add a ticker to the watchlist and start streaming it.

    Raises:
        ValueError: If the ticker is blank or already on the watchlist.
    """
    ticker = _normalize(ticker)
    added = add_watchlist(conn, ticker, user_id)
    if not added:
        raise ValueError(f"{ticker} is already on the watchlist")
    await source.add_ticker(ticker)
    return get_watchlist_with_prices(conn, cache, user_id)


async def remove_from_watchlist(
    conn: sqlite3.Connection,
    source: MarketDataSource,
    cache: PriceCache,
    ticker: str,
    user_id: str = DEFAULT_USER_ID,
) -> list[dict]:
    """Remove a ticker from the watchlist and stop streaming it.

    Removing a ticker that is not present is a no-op (no error).
    """
    ticker = _normalize(ticker)
    remove_watchlist(conn, ticker, user_id)
    await source.remove_ticker(ticker)
    return get_watchlist_with_prices(conn, cache, user_id)
