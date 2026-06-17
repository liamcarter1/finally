"""Unit tests for trade math and portfolio valuation (service layer)."""

from __future__ import annotations

import pytest

from app.db import get_cash_balance, get_position, list_snapshots, list_trades
from app.services import build_portfolio, execute_trade


def test_buy_success_decrements_cash_and_creates_position(conn, cache):
    trade = execute_trade(conn, cache, "AAPL", "buy", 10)
    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"
    assert trade["quantity"] == 10
    assert trade["price"] == 190.0

    assert get_cash_balance(conn) == pytest.approx(10000.0 - 10 * 190.0)
    pos = get_position(conn, "AAPL")
    assert pos is not None
    assert pos["quantity"] == pytest.approx(10)
    assert pos["avg_cost"] == pytest.approx(190.0)


def test_buy_insufficient_cash_raises(conn, cache):
    # 100 * 600 = 60_000 > 10_000
    with pytest.raises(ValueError, match="Insufficient cash"):
        execute_trade(conn, cache, "NFLX", "buy", 100)
    # Nothing changed.
    assert get_cash_balance(conn) == pytest.approx(10000.0)
    assert get_position(conn, "NFLX") is None


def test_buy_averages_cost_across_two_buys(conn, cache):
    execute_trade(conn, cache, "AAPL", "buy", 10)  # @190
    cache.update("AAPL", 210.0)
    execute_trade(conn, cache, "AAPL", "buy", 10)  # @210
    pos = get_position(conn, "AAPL")
    assert pos["quantity"] == pytest.approx(20)
    assert pos["avg_cost"] == pytest.approx(200.0)  # (10*190 + 10*210)/20


def test_sell_success_increments_cash_and_reduces_qty(conn, cache):
    execute_trade(conn, cache, "AAPL", "buy", 10)
    cash_after_buy = get_cash_balance(conn)
    cache.update("AAPL", 200.0)
    execute_trade(conn, cache, "AAPL", "sell", 4)
    assert get_cash_balance(conn) == pytest.approx(cash_after_buy + 4 * 200.0)
    pos = get_position(conn, "AAPL")
    assert pos["quantity"] == pytest.approx(6)
    assert pos["avg_cost"] == pytest.approx(190.0)  # unchanged on sell


def test_sell_entire_position_deletes_it(conn, cache):
    execute_trade(conn, cache, "AAPL", "buy", 5)
    execute_trade(conn, cache, "AAPL", "sell", 5)
    assert get_position(conn, "AAPL") is None


def test_sell_more_than_owned_raises(conn, cache):
    execute_trade(conn, cache, "AAPL", "buy", 3)
    with pytest.raises(ValueError, match="Insufficient shares"):
        execute_trade(conn, cache, "AAPL", "sell", 5)


def test_sell_with_no_position_raises(conn, cache):
    with pytest.raises(ValueError, match="No position"):
        execute_trade(conn, cache, "AAPL", "sell", 1)


def test_unknown_price_ticker_raises(conn, cache):
    with pytest.raises(ValueError, match="No price available"):
        execute_trade(conn, cache, "ZZZZ", "buy", 1)


def test_invalid_quantity_raises(conn, cache):
    with pytest.raises(ValueError, match="greater than 0"):
        execute_trade(conn, cache, "AAPL", "buy", 0)


def test_build_portfolio_totals_and_pnl(conn, cache):
    execute_trade(conn, cache, "AAPL", "buy", 10)  # cost 1900, cash 8100
    cache.update("AAPL", 200.0)  # +10/share unrealized
    portfolio = build_portfolio(conn, cache)

    assert portfolio["cash_balance"] == pytest.approx(8100.0)
    assert portfolio["positions_value"] == pytest.approx(10 * 200.0)
    assert portfolio["total_value"] == pytest.approx(8100.0 + 2000.0)
    assert portfolio["unrealized_pnl"] == pytest.approx((200.0 - 190.0) * 10)

    assert len(portfolio["positions"]) == 1
    p = portfolio["positions"][0]
    assert p["ticker"] == "AAPL"
    assert p["current_price"] == pytest.approx(200.0)
    assert p["market_value"] == pytest.approx(2000.0)
    assert p["unrealized_pnl"] == pytest.approx(100.0)
    assert p["change_percent"] == pytest.approx((200.0 - 190.0) / 190.0 * 100.0)


def test_snapshot_recorded_after_trade(conn, cache):
    assert list_snapshots(conn) == []
    execute_trade(conn, cache, "AAPL", "buy", 1)
    snaps = list_snapshots(conn)
    assert len(snaps) == 1
    # total_value = cash (10000 - 190) + position value (1 * 190) = 10000
    assert snaps[0]["total_value"] == pytest.approx(10000.0)


def test_trade_recorded_in_log(conn, cache):
    execute_trade(conn, cache, "AAPL", "buy", 2)
    trades = list_trades(conn)
    assert len(trades) == 1
    assert trades[0]["ticker"] == "AAPL"
    assert trades[0]["side"] == "buy"
