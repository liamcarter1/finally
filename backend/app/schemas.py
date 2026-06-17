"""Pydantic request/response models for the FinAlly API.

Response bodies are mostly assembled as plain dicts by the service layer; the
models here primarily validate inbound request bodies. A few light response
models are provided for documentation clarity.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TradeRequest(BaseModel):
    """Body for ``POST /api/portfolio/trade``."""

    ticker: str = Field(..., min_length=1, description="Ticker symbol, e.g. AAPL")
    quantity: float = Field(..., gt=0, description="Number of shares (fractional allowed)")
    side: Literal["buy", "sell"]

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("ticker must be a non-empty string")
        return cleaned

    @field_validator("side", mode="before")
    @classmethod
    def _normalize_side(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class WatchlistRequest(BaseModel):
    """Body for ``POST /api/watchlist``."""

    ticker: str = Field(..., min_length=1, description="Ticker symbol to add")

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("ticker must be a non-empty string")
        return cleaned
