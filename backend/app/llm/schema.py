"""Structured-output schema for the LLM chat assistant.

Mirrors the JSON contract in PLAN.md §9 exactly. The LLM is asked to respond
with an object matching :class:`LLMResponse`; we parse it with
``LLMResponse.model_validate_json`` and auto-execute the actions it contains.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LLMTrade(BaseModel):
    """A single trade the assistant wants to auto-execute."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class LLMWatchlistChange(BaseModel):
    """A single watchlist add/remove the assistant wants to perform."""

    ticker: str
    action: Literal["add", "remove"]


class LLMResponse(BaseModel):
    """The full structured response returned by the LLM."""

    message: str
    trades: list[LLMTrade] = Field(default_factory=list)
    watchlist_changes: list[LLMWatchlistChange] = Field(default_factory=list)
