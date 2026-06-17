"""LLM integration for FinAlly.

This package wires the chat assistant to an LLM (via LiteLLM -> OpenRouter ->
Cerebras) using structured outputs, and auto-executes any trades / watchlist
changes the model returns by reusing the existing service layer.

Public API:
    chat(conn, cache, source, user_message, user_id="default") -> dict
    LLMResponse, LLMTrade, LLMWatchlistChange  (structured-output schema)
    router  (FastAPI APIRouter mounting POST /api/chat)
"""

from .router import router
from .schema import LLMResponse, LLMTrade, LLMWatchlistChange
from .service import chat

__all__ = [
    "chat",
    "router",
    "LLMResponse",
    "LLMTrade",
    "LLMWatchlistChange",
]
