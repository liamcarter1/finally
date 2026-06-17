"""Tests for the deterministic mock intent parser."""

from __future__ import annotations

import pytest

from app.llm.mock import mock_response

_PORTFOLIO = {
    "cash_balance": 10000.0,
    "positions_value": 0.0,
    "total_value": 10000.0,
    "unrealized_pnl": 0.0,
    "positions": [],
}
_WATCHLIST = [{"ticker": "AAPL", "price": 190.0, "change_percent": 1.0}]


@pytest.mark.parametrize(
    "message,ticker,side,qty",
    [
        ("buy 5 AAPL", "AAPL", "buy", 5.0),
        ("sell 2 TSLA", "TSLA", "sell", 2.0),
        ("Buy 2.5 nvda please", "NVDA", "buy", 2.5),
        ("buy 5 shares of AAPL", "AAPL", "buy", 5.0),
        ("sell 10 shares MSFT", "MSFT", "sell", 10.0),
    ],
)
def test_trade_intent(message, ticker, side, qty):
    resp = mock_response(message, _PORTFOLIO, _WATCHLIST)
    assert len(resp.trades) == 1
    assert resp.watchlist_changes == []
    t = resp.trades[0]
    assert t.ticker == ticker
    assert t.side == side
    assert t.quantity == qty
    assert resp.message


@pytest.mark.parametrize(
    "message,ticker,action",
    [
        ("add PYPL to watchlist", "PYPL", "add"),
        ("add PYPL to my watchlist", "PYPL", "add"),
        ("remove AAPL from watchlist", "AAPL", "remove"),
        ("watch NFLX", "NFLX", "add"),
        ("unwatch GOOGL", "GOOGL", "remove"),
    ],
)
def test_watchlist_intent(message, ticker, action):
    resp = mock_response(message, _PORTFOLIO, _WATCHLIST)
    assert resp.trades == []
    assert len(resp.watchlist_changes) == 1
    c = resp.watchlist_changes[0]
    assert c.ticker == ticker
    assert c.action == action


def test_analytical_fallback_references_portfolio():
    resp = mock_response("how is my portfolio doing?", _PORTFOLIO, _WATCHLIST)
    assert resp.trades == []
    assert resp.watchlist_changes == []
    assert "10,000.00" in resp.message


def test_mock_is_deterministic():
    a = mock_response("buy 3 AAPL", _PORTFOLIO, _WATCHLIST)
    b = mock_response("buy 3 AAPL", _PORTFOLIO, _WATCHLIST)
    assert a.model_dump() == b.model_dump()
