"""Unit tests for the FinAlly database layer.

All tests use an in-memory or temp-file SQLite database and never touch the
real ``db/finally.db``.
"""

import json
import sqlite3

import pytest

from app.db import database as db
from app.db.database import DEFAULT_CASH_BALANCE, DEFAULT_USER_ID, DEFAULT_WATCHLIST


@pytest.fixture
def conn():
    """A fresh, initialized in-memory database for each test."""
    c = db.get_connection(":memory:")
    db.init_db(c)
    yield c
    c.close()


# --------------------------------------------------------------------------
# Schema + init + seed
# --------------------------------------------------------------------------


def test_schema_creates_all_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    tables = {r["name"] for r in rows}
    expected = {
        "users_profile",
        "watchlist",
        "positions",
        "trades",
        "portfolio_snapshots",
        "chat_messages",
    }
    assert expected.issubset(tables)


def test_connection_row_factory_and_foreign_keys(conn):
    assert conn.row_factory is sqlite3.Row
    fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1


def test_seed_profile(conn):
    profile = db.get_profile(conn)
    assert profile["id"] == DEFAULT_USER_ID
    assert profile["cash_balance"] == DEFAULT_CASH_BALANCE
    assert profile["created_at"]


def test_seed_watchlist(conn):
    # Seed rows share one timestamp, so order is not contractual; compare sets.
    assert set(db.list_watchlist(conn)) == set(DEFAULT_WATCHLIST)
    assert len(db.list_watchlist(conn)) == 10
    assert len(DEFAULT_WATCHLIST) == 10


def test_init_db_is_idempotent(conn):
    db.init_db(conn)
    db.init_db(conn)
    # Still exactly one profile and ten watchlist rows.
    assert conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0] == 1
    assert len(db.list_watchlist(conn)) == 10


def test_init_db_preserves_existing_data(conn):
    db.set_cash_balance(conn, 555.0)
    db.add_watchlist(conn, "PYPL")
    db.init_db(conn)  # must not reseed / clobber
    assert db.get_cash_balance(conn) == 555.0
    assert "PYPL" in db.list_watchlist(conn)


# --------------------------------------------------------------------------
# Path resolution
# --------------------------------------------------------------------------


def test_resolve_db_path_env_override(monkeypatch):
    monkeypatch.setenv(db.DB_PATH_ENV, "/tmp/custom.db")
    assert db.resolve_db_path() == "/tmp/custom.db"


def test_resolve_db_path_default(monkeypatch):
    monkeypatch.delenv(db.DB_PATH_ENV, raising=False)
    path = db.resolve_db_path()
    assert path.replace("\\", "/").endswith("db/finally.db")


def test_get_connection_temp_file(tmp_path):
    db_file = tmp_path / "sub" / "finally.db"
    c = db.get_connection(str(db_file))
    db.init_db(c)
    assert db_file.exists()  # parent dir auto-created
    assert db.get_cash_balance(c) == DEFAULT_CASH_BALANCE
    c.close()


# --------------------------------------------------------------------------
# Profile / cash
# --------------------------------------------------------------------------


def test_get_profile_missing_user_raises(conn):
    with pytest.raises(ValueError):
        db.get_profile(conn, user_id="nope")


def test_set_cash_balance(conn):
    assert db.set_cash_balance(conn, 1234.56) == 1234.56
    assert db.get_cash_balance(conn) == 1234.56


def test_set_cash_balance_missing_user_raises(conn):
    with pytest.raises(ValueError):
        db.set_cash_balance(conn, 1.0, user_id="nope")


# --------------------------------------------------------------------------
# Watchlist
# --------------------------------------------------------------------------


def test_add_watchlist_new(conn):
    assert db.add_watchlist(conn, "PYPL") is True
    assert "PYPL" in db.list_watchlist(conn)


def test_add_watchlist_normalizes_ticker(conn):
    assert db.add_watchlist(conn, "  pypl ") is True
    assert "PYPL" in db.list_watchlist(conn)


def test_add_watchlist_duplicate_is_noop(conn):
    assert db.add_watchlist(conn, "AAPL") is False  # already seeded
    # count unchanged
    assert db.list_watchlist(conn).count("AAPL") == 1


def test_add_watchlist_invalid_raises(conn):
    with pytest.raises(ValueError):
        db.add_watchlist(conn, "   ")


def test_remove_watchlist_existing(conn):
    assert db.remove_watchlist(conn, "AAPL") is True
    assert "AAPL" not in db.list_watchlist(conn)


def test_remove_watchlist_nonexistent_is_noop(conn):
    assert db.remove_watchlist(conn, "ZZZZ") is False


# --------------------------------------------------------------------------
# Positions
# --------------------------------------------------------------------------


def test_get_positions_empty(conn):
    assert db.get_positions(conn) == []


def test_get_position_none(conn):
    assert db.get_position(conn, "AAPL") is None


def test_upsert_position_insert(conn):
    pos = db.upsert_position(conn, "AAPL", 10.0, 190.0)
    assert pos["ticker"] == "AAPL"
    assert pos["quantity"] == 10.0
    assert pos["avg_cost"] == 190.0
    assert db.get_position(conn, "AAPL")["quantity"] == 10.0


def test_upsert_position_update(conn):
    db.upsert_position(conn, "AAPL", 10.0, 190.0)
    pos = db.upsert_position(conn, "AAPL", 15.0, 192.0)
    assert pos["quantity"] == 15.0
    assert pos["avg_cost"] == 192.0
    # Still a single row (unique constraint).
    assert len(db.get_positions(conn)) == 1


def test_delete_position(conn):
    db.upsert_position(conn, "AAPL", 10.0, 190.0)
    assert db.delete_position(conn, "AAPL") is True
    assert db.get_position(conn, "AAPL") is None


def test_delete_position_nonexistent(conn):
    assert db.delete_position(conn, "AAPL") is False


def test_positions_ordered_by_ticker(conn):
    db.upsert_position(conn, "TSLA", 1, 1)
    db.upsert_position(conn, "AAPL", 1, 1)
    db.upsert_position(conn, "MSFT", 1, 1)
    tickers = [p["ticker"] for p in db.get_positions(conn)]
    assert tickers == ["AAPL", "MSFT", "TSLA"]


# --------------------------------------------------------------------------
# Trades
# --------------------------------------------------------------------------


def test_record_trade(conn):
    trade = db.record_trade(conn, "AAPL", "buy", 10.0, 190.0)
    assert trade["ticker"] == "AAPL"
    assert trade["side"] == "buy"
    assert trade["quantity"] == 10.0
    assert trade["price"] == 190.0
    assert trade["executed_at"]


def test_record_trade_side_normalized(conn):
    trade = db.record_trade(conn, "AAPL", "SELL", 1, 1)
    assert trade["side"] == "sell"


def test_record_trade_invalid_side(conn):
    with pytest.raises(ValueError):
        db.record_trade(conn, "AAPL", "hold", 1, 1)


def test_list_trades_recent_first_and_limit(conn):
    for i in range(5):
        db.record_trade(conn, "AAPL", "buy", float(i), 100.0 + i)
    all_trades = db.list_trades(conn)
    assert len(all_trades) == 5
    # Most recent first: last inserted (quantity 4) should be first.
    assert all_trades[0]["quantity"] == 4.0
    limited = db.list_trades(conn, limit=2)
    assert len(limited) == 2
    assert limited[0]["quantity"] == 4.0


# --------------------------------------------------------------------------
# Snapshots
# --------------------------------------------------------------------------


def test_record_and_list_snapshots_chronological(conn):
    for v in (100.0, 110.0, 105.0):
        db.record_snapshot(conn, v)
    snaps = db.list_snapshots(conn)
    values = [s["total_value"] for s in snaps]
    assert values == [100.0, 110.0, 105.0]  # oldest first


def test_list_snapshots_limit_keeps_chronological(conn):
    for v in (100.0, 110.0, 105.0, 120.0):
        db.record_snapshot(conn, v)
    snaps = db.list_snapshots(conn, limit=2)
    values = [s["total_value"] for s in snaps]
    # Newest 2 are 105 and 120, returned oldest-first.
    assert values == [105.0, 120.0]


# --------------------------------------------------------------------------
# Chat messages
# --------------------------------------------------------------------------


def test_add_chat_message_user(conn):
    msg = db.add_chat_message(conn, "user", "hello")
    assert msg["role"] == "user"
    assert msg["content"] == "hello"
    assert msg["actions"] is None


def test_add_chat_message_assistant_with_actions(conn):
    actions = json.dumps({"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 1}]})
    msg = db.add_chat_message(conn, "assistant", "Bought AAPL", actions=actions)
    assert msg["role"] == "assistant"
    assert json.loads(msg["actions"])["trades"][0]["ticker"] == "AAPL"


def test_add_chat_message_invalid_role(conn):
    with pytest.raises(ValueError):
        db.add_chat_message(conn, "system", "nope")


def test_list_chat_messages_chronological_and_limit(conn):
    db.add_chat_message(conn, "user", "m1")
    db.add_chat_message(conn, "assistant", "m2")
    db.add_chat_message(conn, "user", "m3")
    db.add_chat_message(conn, "assistant", "m4")
    all_msgs = db.list_chat_messages(conn)
    assert [m["content"] for m in all_msgs] == ["m1", "m2", "m3", "m4"]
    recent = db.list_chat_messages(conn, limit=2)
    # Newest 2 (m3, m4), returned oldest-first.
    assert [m["content"] for m in recent] == ["m3", "m4"]


# --------------------------------------------------------------------------
# Shared connection singleton
# --------------------------------------------------------------------------


def test_default_connection_singleton(tmp_path, monkeypatch):
    monkeypatch.setenv(db.DB_PATH_ENV, str(tmp_path / "finally.db"))
    db.close_default_connection()
    try:
        c1 = db.get_default_connection()
        c2 = db.get_default_connection()
        assert c1 is c2
        assert db.get_cash_balance(c1) == DEFAULT_CASH_BALANCE
    finally:
        db.close_default_connection()
