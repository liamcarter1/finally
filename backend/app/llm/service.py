"""Chat service: build context, call the LLM, auto-execute actions, persist.

This is the heart of the LLM integration. It reuses the existing service layer
(``app.services``) for all trade/watchlist logic and the DB layer
(``app.db``) for chat persistence -- no trade logic is duplicated here.

Flow (see PLAN.md §9):
    1. Build portfolio context + watchlist-with-prices.
    2. Load recent chat history.
    3. Construct the message list (system prompt + context + history + new msg).
    4. Get an ``LLMResponse`` -- deterministic mock if ``LLM_MOCK`` is truthy,
       otherwise a real LiteLLM -> OpenRouter -> Cerebras structured-output call.
       Malformed / non-JSON responses degrade to a safe fallback message.
    5. Auto-execute trades and watchlist changes, collecting per-item results
       (one failure never aborts the rest).
    6. Persist the user message and the assistant message (with an actions JSON).
    7. Return the API-shaped dict.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3

from app.db import DEFAULT_USER_ID, add_chat_message, list_chat_messages
from app.market import MarketDataSource, PriceCache
from app.services import (
    add_to_watchlist,
    build_portfolio,
    execute_trade,
    get_watchlist_with_prices,
    remove_from_watchlist,
)

from .mock import mock_response
from .prompt import SYSTEM_PROMPT, build_context_block
from .schema import LLMResponse

logger = logging.getLogger(__name__)

#: LiteLLM / OpenRouter / Cerebras configuration (per cerebras-inference skill).
MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

#: How many prior messages to include as conversation history.
HISTORY_LIMIT = 10

_FALLBACK_MESSAGE = (
    "Sorry, I had trouble forming a response just now. Please try rephrasing "
    "your request."
)


def _mock_enabled() -> bool:
    """Return True when LLM_MOCK is set to a truthy value."""
    return os.environ.get("LLM_MOCK", "").strip().lower() in ("1", "true", "yes", "on")


def _build_messages(
    portfolio: dict,
    watchlist: list[dict],
    history: list[dict],
    user_message: str,
) -> list[dict]:
    """Assemble the message list passed to the LLM."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": build_context_block(portfolio, watchlist)},
    ]
    for msg in history:
        role = msg.get("role")
        content = msg.get("content") or ""
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


def _call_llm(messages: list[dict]) -> LLMResponse:
    """Call Cerebras via LiteLLM with structured output, parsing defensively.

    Any error (network, provider, or malformed/non-JSON content) is caught and
    converted into a safe fallback :class:`LLMResponse` so the chat endpoint
    never crashes.
    """
    # Imported lazily so importing this module (and the app) never requires
    # litellm to be installed unless a real call is actually made.
    from litellm import completion

    try:
        response = completion(
            model=MODEL,
            messages=messages,
            response_format=LLMResponse,
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
        )
    except Exception:
        logger.exception("LLM completion call failed")
        return LLMResponse(message=_FALLBACK_MESSAGE)

    return _parse_completion(response)


def _parse_completion(response: object) -> LLMResponse:
    """Extract and validate the structured content from a completion response."""
    try:
        content = response.choices[0].message.content  # type: ignore[attr-defined]
    except (AttributeError, IndexError, TypeError):
        logger.error("LLM response had unexpected shape: %r", response)
        return LLMResponse(message=_FALLBACK_MESSAGE)

    if not content:
        logger.error("LLM returned empty content")
        return LLMResponse(message=_FALLBACK_MESSAGE)

    try:
        return LLMResponse.model_validate_json(content)
    except Exception:
        logger.warning("Failed to parse LLM JSON content: %r", content)
        return LLMResponse(message=_FALLBACK_MESSAGE)


async def chat(
    conn: sqlite3.Connection,
    cache: PriceCache,
    source: MarketDataSource,
    user_message: str,
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    """Process a chat turn and return the API-shaped response dict.

    Returns::

        {
          "message": str,
          "trades": [{ticker, side, quantity, price, status, error?}, ...],
          "watchlist_changes": [{ticker, action, status, error?}, ...],
        }
    """
    portfolio = build_portfolio(conn, cache, user_id)
    watchlist = get_watchlist_with_prices(conn, cache, user_id)
    history = list_chat_messages(conn, limit=HISTORY_LIMIT, user_id=user_id)

    messages = _build_messages(portfolio, watchlist, history, user_message)

    if _mock_enabled():
        resp = mock_response(user_message, portfolio, watchlist)
    else:
        resp = _call_llm(messages)

    # --- Auto-execute trades ---
    trade_results: list[dict] = []
    for trade in resp.trades:
        item: dict = {
            "ticker": trade.ticker,
            "side": trade.side,
            "quantity": trade.quantity,
        }
        try:
            executed = execute_trade(
                conn, cache, trade.ticker, trade.side, trade.quantity, user_id
            )
            item["price"] = executed["price"]
            item["status"] = "executed"
        except ValueError as exc:
            item["price"] = None
            item["status"] = "failed"
            item["error"] = str(exc)
        trade_results.append(item)

    # --- Auto-execute watchlist changes ---
    watchlist_results: list[dict] = []
    for change in resp.watchlist_changes:
        item = {"ticker": change.ticker, "action": change.action}
        try:
            if change.action == "add":
                await add_to_watchlist(conn, source, cache, change.ticker, user_id)
            else:
                await remove_from_watchlist(conn, source, cache, change.ticker, user_id)
            item["status"] = "applied"
        except ValueError as exc:
            item["status"] = "failed"
            item["error"] = str(exc)
        watchlist_results.append(item)

    # --- Persist conversation ---
    add_chat_message(conn, role="user", content=user_message, user_id=user_id)
    actions_json = json.dumps(
        {"trades": trade_results, "watchlist_changes": watchlist_results}
    )
    add_chat_message(
        conn,
        role="assistant",
        content=resp.message,
        actions=actions_json,
        user_id=user_id,
    )

    return {
        "message": resp.message,
        "trades": trade_results,
        "watchlist_changes": watchlist_results,
    }
