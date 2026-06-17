"""Tests for the chat service in mock mode."""

from __future__ import annotations

import json

import pytest

from app.db import list_chat_messages
from app.llm.service import chat
from app.services import build_portfolio, get_watchlist_with_prices


@pytest.mark.asyncio
async def test_chat_returns_valid_shape(conn, cache, source):
    result = await chat(conn, cache, source, "how is my portfolio doing?")
    assert set(result) == {"message", "trades", "watchlist_changes"}
    assert isinstance(result["message"], str) and result["message"]
    assert result["trades"] == []
    assert result["watchlist_changes"] == []


@pytest.mark.asyncio
async def test_buy_executes_and_updates_portfolio(conn, cache, source):
    before = build_portfolio(conn, cache)
    result = await chat(conn, cache, source, "buy 5 AAPL")

    assert len(result["trades"]) == 1
    trade = result["trades"][0]
    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"
    assert trade["quantity"] == 5.0
    assert trade["status"] == "executed"
    assert trade["price"] == 190.0
    assert "error" not in trade

    after = build_portfolio(conn, cache)
    # Cash decreased by 5 * 190 = 950.
    assert after["cash_balance"] == pytest.approx(before["cash_balance"] - 950.0)
    tickers = {p["ticker"] for p in after["positions"]}
    assert "AAPL" in tickers


@pytest.mark.asyncio
async def test_sell_executes(conn, cache, source):
    await chat(conn, cache, source, "buy 5 AAPL")
    result = await chat(conn, cache, source, "sell 2 AAPL")
    trade = result["trades"][0]
    assert trade["side"] == "sell"
    assert trade["status"] == "executed"
    pos = {p["ticker"]: p for p in build_portfolio(conn, cache)["positions"]}
    assert pos["AAPL"]["quantity"] == pytest.approx(3.0)


@pytest.mark.asyncio
async def test_failed_trade_insufficient_cash(conn, cache, source):
    # 1000 shares of AAPL @ 190 = 190,000 > 10,000 cash.
    result = await chat(conn, cache, source, "buy 1000 AAPL")
    trade = result["trades"][0]
    assert trade["status"] == "failed"
    assert "error" in trade and trade["error"]
    # Portfolio unchanged (no position created).
    assert build_portfolio(conn, cache)["positions"] == []
    # Did not crash; message still present.
    assert result["message"]


@pytest.mark.asyncio
async def test_failed_trade_unknown_ticker(conn, cache, source):
    # ZZZ has no price in the cache -> execute_trade raises ValueError.
    result = await chat(conn, cache, source, "buy 1 ZZZ")
    trade = result["trades"][0]
    assert trade["status"] == "failed"
    assert "error" in trade


@pytest.mark.asyncio
async def test_watchlist_add_intent(conn, cache, source):
    result = await chat(conn, cache, source, "add PYPL to watchlist")
    assert len(result["watchlist_changes"]) == 1
    change = result["watchlist_changes"][0]
    assert change["ticker"] == "PYPL"
    assert change["action"] == "add"
    assert change["status"] == "applied"
    tickers = {w["ticker"] for w in get_watchlist_with_prices(conn, cache)}
    assert "PYPL" in tickers
    assert "PYPL" in source.added


@pytest.mark.asyncio
async def test_watchlist_remove_intent(conn, cache, source):
    result = await chat(conn, cache, source, "remove AAPL from watchlist")
    change = result["watchlist_changes"][0]
    assert change["action"] == "remove"
    assert change["status"] == "applied"
    tickers = {w["ticker"] for w in get_watchlist_with_prices(conn, cache)}
    assert "AAPL" not in tickers


@pytest.mark.asyncio
async def test_watchlist_add_duplicate_fails(conn, cache, source):
    # AAPL is already a default watchlist entry -> ValueError.
    result = await chat(conn, cache, source, "add AAPL to watchlist")
    change = result["watchlist_changes"][0]
    assert change["status"] == "failed"
    assert "error" in change


@pytest.mark.asyncio
async def test_messages_persisted(conn, cache, source):
    await chat(conn, cache, source, "buy 5 AAPL")
    msgs = list_chat_messages(conn)
    assert len(msgs) == 2
    user_msg, assistant_msg = msgs
    assert user_msg["role"] == "user"
    assert user_msg["content"] == "buy 5 AAPL"
    assert user_msg["actions"] is None
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"]
    # Assistant row carries an actions JSON capturing executed trades.
    actions = json.loads(assistant_msg["actions"])
    assert actions["trades"][0]["ticker"] == "AAPL"
    assert actions["trades"][0]["status"] == "executed"


@pytest.mark.asyncio
async def test_history_loaded_into_prompt(conn, cache, source, monkeypatch):
    """Prior turns should be fed back into the constructed message list."""
    # First turn establishes history.
    await chat(conn, cache, source, "how is my portfolio doing?")

    captured = {}
    from app.llm import service as svc

    original = svc._build_messages

    def spy(portfolio, watchlist, history, user_message):
        captured["history"] = history
        captured["messages"] = original(portfolio, watchlist, history, user_message)
        return captured["messages"]

    monkeypatch.setattr(svc, "_build_messages", spy)

    await chat(conn, cache, source, "and now?")

    # The earlier user message should be present in history + the message list.
    assert any(
        m["role"] == "user" and m["content"] == "how is my portfolio doing?"
        for m in captured["history"]
    )
    assert any(
        m.get("content") == "how is my portfolio doing?" for m in captured["messages"]
    )
