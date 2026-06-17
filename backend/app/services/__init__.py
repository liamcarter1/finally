"""Business-logic services for FinAlly.

These functions contain the core trade/portfolio/watchlist logic and are
intentionally callable without any HTTP context so the LLM layer can reuse
them directly.
"""

from .portfolio import build_portfolio, execute_trade, record_portfolio_snapshot
from .watchlist import (
    add_to_watchlist,
    get_watchlist_with_prices,
    remove_from_watchlist,
)

__all__ = [
    "build_portfolio",
    "execute_trade",
    "record_portfolio_snapshot",
    "get_watchlist_with_prices",
    "add_to_watchlist",
    "remove_from_watchlist",
]
