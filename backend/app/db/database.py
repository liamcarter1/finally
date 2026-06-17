"""SQLite data-access layer for FinAlly.

This module owns the database schema, lazy initialization, default-data
seeding, connection management, and a set of small data-access functions
that the Backend and LLM engineers compose into higher-level logic.

Design notes
------------
Connection / concurrency:
    The FastAPI app runs as a single process. Both request handlers and
    background tasks (portfolio snapshots) write to the same SQLite file.
    We use a single shared connection created with
    ``check_same_thread=False`` and guard *every* operation with a
    module-level ``threading.RLock`` (see ``_LOCK``). SQLite serializes
    writes anyway; the lock makes our multi-statement reads/writes (e.g.
    upserts) atomic with respect to each other across threads and avoids
    "recursive use of cursors" / threading errors.

    Callers obtain a connection via :func:`get_default_connection` (the
    shared, lazily-initialized singleton) or :func:`get_connection` (a
    fresh connection, used for tests and for the ``:memory:`` case). All
    data-access functions take an explicit ``conn`` argument so they are
    easy to test and do not rely on global state.

Timestamps:
    Stored as ISO 8601 UTC strings via ``datetime.now(timezone.utc).isoformat()``.

IDs:
    Generated with ``uuid4().hex``.

This layer deliberately does NOT implement trade math or P&L. It provides
persistence primitives only (``upsert_position``, ``record_trade``, ...).
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0

#: Default tickers seeded into the watchlist on first initialization.
DEFAULT_WATCHLIST = (
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
)

#: Environment variable that overrides the database file path.
DB_PATH_ENV = "FINALLY_DB_PATH"

#: Path to the schema DDL, shipped at backend/db/schema.sql.
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"

#: Default database location: <project_root>/db/finally.db
#: __file__ = backend/app/db/database.py -> parents[3] = project root.
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "db" / "finally.db"


# --------------------------------------------------------------------------
# Internal shared-connection state
# --------------------------------------------------------------------------

_LOCK = threading.RLock()
_shared_conn: sqlite3.Connection | None = None


def _utcnow_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Return a fresh hex UUID for use as a primary key."""
    return uuid4().hex


# --------------------------------------------------------------------------
# Path resolution & connection management
# --------------------------------------------------------------------------


def resolve_db_path() -> str:
    """Resolve the database path.

    Uses the ``FINALLY_DB_PATH`` environment variable if set and non-empty,
    otherwise falls back to ``<project_root>/db/finally.db``. The literal
    value ``":memory:"`` is passed through unchanged for in-memory use.
    """
    env_value = os.environ.get(DB_PATH_ENV)
    if env_value:
        return env_value
    return str(_DEFAULT_DB_PATH)


def _ensure_parent_dir(db_path: str) -> None:
    """Create the parent directory for ``db_path`` if needed.

    No-op for the in-memory database.
    """
    if db_path == ":memory:":
        return
    parent = Path(db_path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Create and return a *new* SQLite connection.

    The connection has ``row_factory = sqlite3.Row`` and ``PRAGMA
    foreign_keys = ON``. ``check_same_thread`` is disabled so the connection
    may be shared across threads (callers must serialize access; the shared
    singleton does this via the module lock).

    Args:
        db_path: Explicit path, or ``":memory:"``. When ``None`` the path is
            resolved via :func:`resolve_db_path`.

    Returns:
        A configured :class:`sqlite3.Connection`. The caller owns its
        lifecycle and is responsible for closing it (except for the shared
        singleton returned by :func:`get_default_connection`).
    """
    if db_path is None:
        db_path = resolve_db_path()
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_default_connection() -> sqlite3.Connection:
    """Return the process-wide shared, initialized connection.

    Lazily creates the connection (at the path from
    :func:`resolve_db_path`) and runs :func:`init_db` the first time it is
    called. Subsequent calls return the same object. Thread-safe.
    """
    global _shared_conn
    with _LOCK:
        if _shared_conn is None:
            conn = get_connection()
            init_db(conn)
            _shared_conn = conn
        return _shared_conn


def close_default_connection() -> None:
    """Close and clear the shared connection (mainly for tests/shutdown)."""
    global _shared_conn
    with _LOCK:
        if _shared_conn is not None:
            _shared_conn.close()
            _shared_conn = None


# --------------------------------------------------------------------------
# Schema creation + seeding
# --------------------------------------------------------------------------


def _load_schema_sql() -> str:
    """Read the schema DDL from disk."""
    return _SCHEMA_PATH.read_text(encoding="utf-8")


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables if missing and seed default data if empty.

    Idempotent: safe to call repeatedly. Creates the schema from
    ``schema.sql`` then ensures exactly one default user profile and the
    default watchlist exist. Existing data is never overwritten.
    """
    with _LOCK:
        conn.executescript(_load_schema_sql())
        _seed_if_empty(conn)
        conn.commit()


#: Backwards/alternative-name alias for :func:`init_db`.
ensure_initialized = init_db


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    """Seed the default user profile and watchlist if they are absent."""
    now = _utcnow_iso()

    profile_count = conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
    if profile_count == 0:
        conn.execute(
            "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
        )

    watch_count = conn.execute(
        "SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (DEFAULT_USER_ID,)
    ).fetchone()[0]
    if watch_count == 0:
        conn.executemany(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            [(_new_id(), DEFAULT_USER_ID, ticker, now) for ticker in DEFAULT_WATCHLIST],
        )


# --------------------------------------------------------------------------
# Ticker normalization
# --------------------------------------------------------------------------


def _normalize_ticker(ticker: str) -> str:
    """Validate and normalize a ticker to upper-case, no surrounding space.

    Raises:
        ValueError: If ``ticker`` is empty/blank.
    """
    if not isinstance(ticker, str):
        raise ValueError("ticker must be a string")
    cleaned = ticker.strip().upper()
    if not cleaned:
        raise ValueError("ticker must be a non-empty string")
    return cleaned


# --------------------------------------------------------------------------
# Profile / cash
# --------------------------------------------------------------------------


def get_profile(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> dict:
    """Return the user profile as a dict.

    Keys: ``id``, ``cash_balance``, ``created_at``.

    Raises:
        ValueError: If no profile exists for ``user_id``.
    """
    with _LOCK:
        row = conn.execute(
            "SELECT id, cash_balance, created_at FROM users_profile WHERE id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"No profile for user_id={user_id!r}")
    return dict(row)


def get_cash_balance(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> float:
    """Return the user's current cash balance."""
    return float(get_profile(conn, user_id)["cash_balance"])


def set_cash_balance(
    conn: sqlite3.Connection, balance: float, user_id: str = DEFAULT_USER_ID
) -> float:
    """Set the user's cash balance and return the new value.

    Raises:
        ValueError: If no profile exists for ``user_id``.
    """
    with _LOCK:
        cur = conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (float(balance), user_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"No profile for user_id={user_id!r}")
        conn.commit()
    return float(balance)


# --------------------------------------------------------------------------
# Watchlist
# --------------------------------------------------------------------------


def list_watchlist(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> list[str]:
    """Return the user's watchlist tickers, ordered by when they were added."""
    with _LOCK:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, ticker",
            (user_id,),
        ).fetchall()
    return [row["ticker"] for row in rows]


def add_watchlist(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> bool:
    """Add a ticker to the watchlist (idempotent).

    The ticker is upper-cased and stripped. Adding a duplicate is a no-op
    (returns ``False``); a fresh add returns ``True``.

    Raises:
        ValueError: If ``ticker`` is empty/blank.
    """
    ticker = _normalize_ticker(ticker)
    with _LOCK:
        cur = conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) "
            "VALUES (?, ?, ?, ?)",
            (_new_id(), user_id, ticker, _utcnow_iso()),
        )
        conn.commit()
    return cur.rowcount > 0


def remove_watchlist(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> bool:
    """Remove a ticker from the watchlist.

    Returns ``True`` if a row was removed, ``False`` if the ticker was not
    present (removing a nonexistent ticker is a safe no-op).

    Raises:
        ValueError: If ``ticker`` is empty/blank.
    """
    ticker = _normalize_ticker(ticker)
    with _LOCK:
        cur = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        conn.commit()
    return cur.rowcount > 0


# --------------------------------------------------------------------------
# Positions
# --------------------------------------------------------------------------


def get_positions(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> list[dict]:
    """Return all positions for the user as a list of dicts.

    Each dict has keys: ``id``, ``user_id``, ``ticker``, ``quantity``,
    ``avg_cost``, ``updated_at``. Ordered by ticker.
    """
    with _LOCK:
        rows = conn.execute(
            "SELECT id, user_id, ticker, quantity, avg_cost, updated_at "
            "FROM positions WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_position(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> dict | None:
    """Return a single position dict for ``ticker``, or ``None`` if absent.

    Raises:
        ValueError: If ``ticker`` is empty/blank.
    """
    ticker = _normalize_ticker(ticker)
    with _LOCK:
        row = conn.execute(
            "SELECT id, user_id, ticker, quantity, avg_cost, updated_at "
            "FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
    return dict(row) if row is not None else None


def upsert_position(
    conn: sqlite3.Connection,
    ticker: str,
    quantity: float,
    avg_cost: float,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Insert or update a position (raw write; no trade math).

    Creates the position if it does not exist, otherwise overwrites
    ``quantity`` and ``avg_cost`` and refreshes ``updated_at``. Returns the
    resulting position dict.

    Note: this does NOT auto-delete on zero quantity; use
    :func:`delete_position` for that. The Backend engineer decides the
    policy.

    Raises:
        ValueError: If ``ticker`` is empty/blank.
    """
    ticker = _normalize_ticker(ticker)
    now = _utcnow_iso()
    with _LOCK:
        conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id, ticker) DO UPDATE SET "
            "quantity = excluded.quantity, "
            "avg_cost = excluded.avg_cost, "
            "updated_at = excluded.updated_at",
            (_new_id(), user_id, ticker, float(quantity), float(avg_cost), now),
        )
        conn.commit()
    position = get_position(conn, ticker, user_id)
    assert position is not None  # just upserted
    return position


def delete_position(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> bool:
    """Delete a position (e.g. when quantity reaches 0).

    Returns ``True`` if a row was deleted, ``False`` if none existed.

    Raises:
        ValueError: If ``ticker`` is empty/blank.
    """
    ticker = _normalize_ticker(ticker)
    with _LOCK:
        cur = conn.execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        conn.commit()
    return cur.rowcount > 0


# --------------------------------------------------------------------------
# Trades
# --------------------------------------------------------------------------


def record_trade(
    conn: sqlite3.Connection,
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Append a trade to the trade log (raw write; no validation/math).

    ``side`` must be ``"buy"`` or ``"sell"`` (case-insensitive). Returns the
    stored trade dict with keys: ``id``, ``user_id``, ``ticker``, ``side``,
    ``quantity``, ``price``, ``executed_at``.

    Raises:
        ValueError: If ``ticker`` is empty/blank or ``side`` is invalid.
    """
    ticker = _normalize_ticker(ticker)
    side_norm = side.strip().lower() if isinstance(side, str) else ""
    if side_norm not in ("buy", "sell"):
        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
    trade_id = _new_id()
    executed_at = _utcnow_iso()
    with _LOCK:
        conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, user_id, ticker, side_norm, float(quantity), float(price), executed_at),
        )
        conn.commit()
    return {
        "id": trade_id,
        "user_id": user_id,
        "ticker": ticker,
        "side": side_norm,
        "quantity": float(quantity),
        "price": float(price),
        "executed_at": executed_at,
    }


def list_trades(
    conn: sqlite3.Connection,
    user_id: str = DEFAULT_USER_ID,
    limit: int | None = None,
) -> list[dict]:
    """Return trades for the user, most recent first.

    Args:
        limit: Maximum number of trades to return. ``None`` returns all.
    """
    sql = (
        "SELECT id, user_id, ticker, side, quantity, price, executed_at "
        "FROM trades WHERE user_id = ? ORDER BY executed_at DESC, id DESC"
    )
    params: list = [user_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))
    with _LOCK:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


# --------------------------------------------------------------------------
# Portfolio snapshots
# --------------------------------------------------------------------------


def record_snapshot(
    conn: sqlite3.Connection,
    total_value: float,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Record a portfolio total-value snapshot. Returns the stored dict."""
    snap_id = _new_id()
    recorded_at = _utcnow_iso()
    with _LOCK:
        conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (snap_id, user_id, float(total_value), recorded_at),
        )
        conn.commit()
    return {
        "id": snap_id,
        "user_id": user_id,
        "total_value": float(total_value),
        "recorded_at": recorded_at,
    }


def list_snapshots(
    conn: sqlite3.Connection,
    user_id: str = DEFAULT_USER_ID,
    limit: int | None = None,
) -> list[dict]:
    """Return portfolio snapshots in chronological order (oldest first).

    Suitable for plotting a P&L time series directly. When ``limit`` is set,
    the most recent ``limit`` snapshots are returned, still in chronological
    order.
    """
    with _LOCK:
        if limit is None:
            rows = conn.execute(
                "SELECT id, user_id, total_value, recorded_at "
                "FROM portfolio_snapshots WHERE user_id = ? "
                "ORDER BY recorded_at, id",
                (user_id,),
            ).fetchall()
        else:
            # Take the newest `limit`, then re-sort ascending for plotting.
            rows = conn.execute(
                "SELECT id, user_id, total_value, recorded_at FROM ("
                "  SELECT id, user_id, total_value, recorded_at "
                "  FROM portfolio_snapshots WHERE user_id = ? "
                "  ORDER BY recorded_at DESC, id DESC LIMIT ?"
                ") ORDER BY recorded_at, id",
                (user_id, int(limit)),
            ).fetchall()
    return [dict(row) for row in rows]


# --------------------------------------------------------------------------
# Chat messages
# --------------------------------------------------------------------------


def add_chat_message(
    conn: sqlite3.Connection,
    role: str,
    content: str,
    actions: str | None = None,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Append a chat message and return the stored dict.

    Args:
        role: ``"user"`` or ``"assistant"``.
        content: Message text.
        actions: Optional JSON string describing executed actions (trades,
            watchlist changes). The caller is responsible for serializing to
            JSON; this layer stores it verbatim. Typically ``None`` for user
            messages.

    Raises:
        ValueError: If ``role`` is invalid.
    """
    role_norm = role.strip().lower() if isinstance(role, str) else ""
    if role_norm not in ("user", "assistant"):
        raise ValueError(f"role must be 'user' or 'assistant', got {role!r}")
    msg_id = _new_id()
    created_at = _utcnow_iso()
    with _LOCK:
        conn.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, user_id, role_norm, content, actions, created_at),
        )
        conn.commit()
    return {
        "id": msg_id,
        "user_id": user_id,
        "role": role_norm,
        "content": content,
        "actions": actions,
        "created_at": created_at,
    }


def list_chat_messages(
    conn: sqlite3.Connection,
    limit: int | None = None,
    user_id: str = DEFAULT_USER_ID,
) -> list[dict]:
    """Return chat messages in chronological order (oldest first).

    When ``limit`` is provided, the most recent ``limit`` messages are
    returned, still ordered oldest-first (ready to render as a transcript).

    Each dict has keys: ``id``, ``user_id``, ``role``, ``content``,
    ``actions``, ``created_at``.
    """
    with _LOCK:
        if limit is None:
            rows = conn.execute(
                "SELECT id, user_id, role, content, actions, created_at "
                "FROM chat_messages WHERE user_id = ? "
                "ORDER BY created_at, id",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, user_id, role, content, actions, created_at FROM ("
                "  SELECT id, user_id, role, content, actions, created_at "
                "  FROM chat_messages WHERE user_id = ? "
                "  ORDER BY created_at DESC, id DESC LIMIT ?"
                ") ORDER BY created_at, id",
                (user_id, int(limit)),
            ).fetchall()
    return [dict(row) for row in rows]
