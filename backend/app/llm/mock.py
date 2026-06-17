"""Deterministic mock LLM for offline / CI / E2E use.

When ``LLM_MOCK`` is truthy, the chat service calls :func:`mock_response`
instead of the network. The mock parses simple, predictable intent from the
user's message with regular expressions so that E2E flows (e.g. "send a
message -> trade executes inline") are fully deterministic and require no API
key or network access.

Mock grammar (case-insensitive; first match wins):

    Trades:
        "buy <qty> <TICKER>"     -> trade {ticker, side="buy",  quantity=<qty>}
        "sell <qty> <TICKER>"    -> trade {ticker, side="sell", quantity=<qty>}
      The word "shares" between qty and ticker is optional and ignored, e.g.
        "buy 5 shares of AAPL"   also matches.

    Watchlist:
        "add <TICKER> to watchlist"        -> watchlist_change {ticker, action="add"}
        "add <TICKER> to my watchlist"     -> same
        "remove <TICKER> from watchlist"   -> watchlist_change {ticker, action="remove"}
        "watch <TICKER>"                   -> add
        "unwatch <TICKER>"                 -> remove

    Anything else:
        Returns a canned analytical message referencing the actual portfolio
        context (cash + total value + position count), with no actions.

Tickers are 1-5 uppercase letters. Quantities may be integers or decimals.
Only the FIRST matching action is emitted (one trade OR one watchlist change),
which keeps the behavior simple and predictable for tests.
"""

from __future__ import annotations

import re

from .schema import LLMResponse, LLMTrade, LLMWatchlistChange

_TICKER = r"([A-Za-z]{1,5})"
_QTY = r"(\d+(?:\.\d+)?)"

# "buy 5 AAPL", "buy 5 shares of AAPL", "sell 2.5 TSLA"
_TRADE_RE = re.compile(
    rf"\b(buy|sell)\s+{_QTY}\s+(?:shares?\s+(?:of\s+)?)?{_TICKER}\b",
    re.IGNORECASE,
)

# "add PYPL to (my) watchlist", "remove X from (my) watchlist"
_WATCHLIST_PHRASE_RE = re.compile(
    rf"\b(add|remove)\s+{_TICKER}\s+(?:to|from)\s+(?:my\s+)?watchlist\b",
    re.IGNORECASE,
)

# "watch PYPL" / "unwatch X"
_WATCH_VERB_RE = re.compile(rf"\b(unwatch|watch)\s+{_TICKER}\b", re.IGNORECASE)


def mock_response(user_message: str, portfolio: dict, watchlist: list[dict]) -> LLMResponse:
    """Return a deterministic :class:`LLMResponse` for ``user_message``."""
    text = user_message or ""

    trade_match = _TRADE_RE.search(text)
    if trade_match:
        side = trade_match.group(1).lower()
        quantity = float(trade_match.group(2))
        ticker = trade_match.group(3).upper()
        verb = "Buying" if side == "buy" else "Selling"
        return LLMResponse(
            message=f"{verb} {quantity:g} share(s) of {ticker} at the current market price.",
            trades=[LLMTrade(ticker=ticker, side=side, quantity=quantity)],
        )

    wl_match = _WATCHLIST_PHRASE_RE.search(text)
    if wl_match:
        action = wl_match.group(1).lower()
        ticker = wl_match.group(2).upper()
        verb = "Adding" if action == "add" else "Removing"
        prep = "to" if action == "add" else "from"
        return LLMResponse(
            message=f"{verb} {ticker} {prep} your watchlist.",
            watchlist_changes=[LLMWatchlistChange(ticker=ticker, action=action)],
        )

    watch_match = _WATCH_VERB_RE.search(text)
    if watch_match:
        verb_word = watch_match.group(1).lower()
        action = "remove" if verb_word == "unwatch" else "add"
        ticker = watch_match.group(2).upper()
        verb = "Adding" if action == "add" else "Removing"
        prep = "to" if action == "add" else "from"
        return LLMResponse(
            message=f"{verb} {ticker} {prep} your watchlist.",
            watchlist_changes=[LLMWatchlistChange(ticker=ticker, action=action)],
        )

    # Canned analytical fallback referencing real context.
    positions = portfolio.get("positions") or []
    pos_count = len(positions)
    pos_desc = "no open positions" if pos_count == 0 else f"{pos_count} open position(s)"
    message = (
        f"Your portfolio is worth ${portfolio['total_value']:,.2f} "
        f"with ${portfolio['cash_balance']:,.2f} in cash and {pos_desc}. "
        f"Total unrealized P&L is ${portfolio['unrealized_pnl']:,.2f}. "
        "Let me know if you'd like to buy, sell, or adjust your watchlist."
    )
    return LLMResponse(message=message)
