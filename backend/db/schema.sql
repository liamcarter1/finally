-- FinAlly database schema (SQLite).
--
-- All tables carry a `user_id` column defaulting to 'default'. This is
-- hardcoded for the current single-user model but lets us add real
-- multi-user support later without a schema migration.
--
-- All timestamps are stored as ISO 8601 strings (UTC),
-- e.g. datetime.now(timezone.utc).isoformat().
--
-- This file is applied by app.db.database.init_db(). Every statement is
-- idempotent (IF NOT EXISTS) so applying it repeatedly is safe.

-- User state: cash balance and profile creation time.
CREATE TABLE IF NOT EXISTS users_profile (
    id           TEXT PRIMARY KEY DEFAULT 'default',
    cash_balance REAL NOT NULL DEFAULT 10000.0,
    created_at   TEXT NOT NULL
);

-- Tickers the user is watching.
CREATE TABLE IF NOT EXISTS watchlist (
    id       TEXT PRIMARY KEY,
    user_id  TEXT NOT NULL DEFAULT 'default',
    ticker   TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
);

-- Current holdings: one row per ticker per user. Fractional shares allowed.
CREATE TABLE IF NOT EXISTS positions (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'default',
    ticker     TEXT NOT NULL,
    quantity   REAL NOT NULL,
    avg_cost   REAL NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (user_id, ticker)
);

-- Append-only trade log.
CREATE TABLE IF NOT EXISTS trades (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL DEFAULT 'default',
    ticker      TEXT NOT NULL,
    side        TEXT NOT NULL,           -- 'buy' or 'sell'
    quantity    REAL NOT NULL,
    price       REAL NOT NULL,
    executed_at TEXT NOT NULL
);

-- Portfolio total value over time (for the P&L chart).
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL DEFAULT 'default',
    total_value REAL NOT NULL,
    recorded_at TEXT NOT NULL
);

-- Conversation history with the LLM assistant.
CREATE TABLE IF NOT EXISTS chat_messages (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL DEFAULT 'default',
    role       TEXT NOT NULL,            -- 'user' or 'assistant'
    content    TEXT NOT NULL,
    actions    TEXT,                     -- JSON; null for user messages
    created_at TEXT NOT NULL
);

-- Helpful indexes for the common time-ordered reads.
CREATE INDEX IF NOT EXISTS idx_trades_user_time
    ON trades (user_id, executed_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_user_time
    ON portfolio_snapshots (user_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_chat_user_time
    ON chat_messages (user_id, created_at);
