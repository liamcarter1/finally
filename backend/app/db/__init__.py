"""Database subsystem for FinAlly.

A self-contained SQLite data-access layer: schema, lazy initialization,
seeding, connection management, and small persistence primitives.

Connection model:
    The app is single-process. ``get_default_connection()`` returns a
    shared, lazily-initialized connection; all access is serialized by an
    internal module lock so request handlers and background tasks can both
    write safely. Tests use ``get_connection(":memory:")`` plus
    ``init_db(conn)``.

Public API (all data-access functions take an explicit ``conn``):
    Connection / init:
        get_connection, get_default_connection, close_default_connection,
        init_db, ensure_initialized, resolve_db_path
    Profile / cash:
        get_profile, get_cash_balance, set_cash_balance
    Watchlist:
        list_watchlist, add_watchlist, remove_watchlist
    Positions:
        get_positions, get_position, upsert_position, delete_position
    Trades:
        record_trade, list_trades
    Snapshots:
        record_snapshot, list_snapshots
    Chat:
        add_chat_message, list_chat_messages
    Constants:
        DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, DEFAULT_WATCHLIST, DB_PATH_ENV
"""

from .database import (
    DB_PATH_ENV,
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    DEFAULT_WATCHLIST,
    add_chat_message,
    add_watchlist,
    close_default_connection,
    delete_position,
    ensure_initialized,
    get_cash_balance,
    get_connection,
    get_default_connection,
    get_position,
    get_positions,
    get_profile,
    init_db,
    list_chat_messages,
    list_snapshots,
    list_trades,
    list_watchlist,
    record_snapshot,
    record_trade,
    remove_watchlist,
    resolve_db_path,
    set_cash_balance,
    upsert_position,
)

__all__ = [
    # connection / init
    "get_connection",
    "get_default_connection",
    "close_default_connection",
    "init_db",
    "ensure_initialized",
    "resolve_db_path",
    # profile / cash
    "get_profile",
    "get_cash_balance",
    "set_cash_balance",
    # watchlist
    "list_watchlist",
    "add_watchlist",
    "remove_watchlist",
    # positions
    "get_positions",
    "get_position",
    "upsert_position",
    "delete_position",
    # trades
    "record_trade",
    "list_trades",
    # snapshots
    "record_snapshot",
    "list_snapshots",
    # chat
    "add_chat_message",
    "list_chat_messages",
    # constants
    "DEFAULT_USER_ID",
    "DEFAULT_CASH_BALANCE",
    "DEFAULT_WATCHLIST",
    "DB_PATH_ENV",
]
