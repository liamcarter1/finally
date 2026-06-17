"""FastAPI dependencies that inject shared state into request handlers.

The DB connection, price cache, and market-data source are created once
during app startup and stored on ``app.state``. These dependencies pull them
back out so handlers and the service layer stay decoupled from globals.
"""

from __future__ import annotations

import sqlite3

from fastapi import Request

from app.market import MarketDataSource, PriceCache


def get_conn(request: Request) -> sqlite3.Connection:
    """Return the shared SQLite connection stored on app state."""
    return request.app.state.db_conn


def get_cache(request: Request) -> PriceCache:
    """Return the shared PriceCache stored on app state."""
    return request.app.state.price_cache


def get_source(request: Request) -> MarketDataSource:
    """Return the shared market data source stored on app state."""
    return request.app.state.market_source
