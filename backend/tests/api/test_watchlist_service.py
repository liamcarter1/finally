"""Unit tests for watchlist service logic."""

from __future__ import annotations

import pytest

from app.db import list_watchlist
from app.services import (
    add_to_watchlist,
    get_watchlist_with_prices,
    remove_from_watchlist,
)


def test_get_watchlist_with_prices_includes_seeded(conn, cache):
    rows = get_watchlist_with_prices(conn, cache)
    tickers = {r["ticker"] for r in rows}
    assert "AAPL" in tickers
    aapl = next(r for r in rows if r["ticker"] == "AAPL")
    assert aapl["price"] == 190.0
    assert aapl["direction"] in ("up", "down", "flat")


def test_get_watchlist_with_prices_null_when_no_tick(conn):
    from app.market import PriceCache

    empty = PriceCache()
    rows = get_watchlist_with_prices(conn, empty)
    assert rows[0]["price"] is None
    assert rows[0]["change_percent"] is None


async def test_add_to_watchlist_updates_source(conn, cache, source):
    rows = await add_to_watchlist(conn, source, cache, "pypl")
    assert "PYPL" in list_watchlist(conn)
    assert "PYPL" in source.added
    assert any(r["ticker"] == "PYPL" for r in rows)


async def test_add_duplicate_raises(conn, cache, source):
    with pytest.raises(ValueError, match="already on the watchlist"):
        await add_to_watchlist(conn, source, cache, "AAPL")


async def test_remove_from_watchlist_updates_source(conn, cache, source):
    rows = await remove_from_watchlist(conn, source, cache, "AAPL")
    assert "AAPL" not in list_watchlist(conn)
    assert "AAPL" in source.removed
    assert all(r["ticker"] != "AAPL" for r in rows)
