"""Fixtures for LLM chat tests.

Mirrors tests/api/conftest.py: an isolated in-memory SQLite DB, a manually
seeded PriceCache, and a fake market-data source. No network and no live
simulator are involved.
"""

from __future__ import annotations

import pytest

from app.db import get_connection, init_db
from app.market import PriceCache


class FakeSource:
    """Minimal MarketDataSource stand-in that records add/remove calls."""

    def __init__(self) -> None:
        self.tickers: list[str] = []
        self.added: list[str] = []
        self.removed: list[str] = []

    async def start(self, tickers):
        self.tickers = list(tickers)

    async def stop(self):
        pass

    async def add_ticker(self, ticker: str) -> None:
        self.added.append(ticker)
        if ticker not in self.tickers:
            self.tickers.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self.removed.append(ticker)
        if ticker in self.tickers:
            self.tickers.remove(ticker)

    def get_tickers(self):
        return list(self.tickers)


@pytest.fixture
def conn():
    """Fresh in-memory database, schema created + default data seeded."""
    connection = get_connection(":memory:")
    init_db(connection)
    yield connection
    connection.close()


@pytest.fixture
def cache():
    """PriceCache seeded with deterministic prices for the default tickers."""
    c = PriceCache()
    seed = {
        "AAPL": 190.0,
        "GOOGL": 175.0,
        "MSFT": 420.0,
        "AMZN": 185.0,
        "TSLA": 250.0,
        "NVDA": 120.0,
        "META": 500.0,
        "JPM": 200.0,
        "V": 280.0,
        "NFLX": 600.0,
    }
    for ticker, price in seed.items():
        c.update(ticker, price)
    return c


@pytest.fixture
def source():
    return FakeSource()


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    """Default every LLM test to mock mode unless it opts out explicitly."""
    monkeypatch.setenv("LLM_MOCK", "true")
