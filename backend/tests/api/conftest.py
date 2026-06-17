"""Shared fixtures for service + API tests.

These tests run against an isolated in-memory SQLite DB and a manually-seeded
PriceCache. They do NOT depend on the live simulator background task or the
app lifespan: an app fixture wires the shared state onto ``app.state``
directly and overrides the dependency injectors.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_cache, get_conn, get_source
from app.db import get_connection, init_db
from app.main import app as fastapi_app
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


@pytest.fixture
def client(conn, cache, source):
    """TestClient with app.state and DI wired to the test fixtures.

    Dependency overrides bypass the lifespan, so no real market source or
    background task runs during API tests.
    """
    fastapi_app.dependency_overrides[get_conn] = lambda: conn
    fastapi_app.dependency_overrides[get_cache] = lambda: cache
    fastapi_app.dependency_overrides[get_source] = lambda: source

    # Some handlers read request.app.state directly via deps; populate it too.
    fastapi_app.state.db_conn = conn
    fastapi_app.state.price_cache = cache
    fastapi_app.state.market_source = source

    # Do not trigger the lifespan (which would start the real simulator).
    test_client = TestClient(fastapi_app, raise_server_exceptions=True)
    test_client.app = fastapi_app
    yield test_client

    fastapi_app.dependency_overrides.clear()
