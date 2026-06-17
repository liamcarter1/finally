"""Structured-output parsing + error-handling tests.

These patch ``litellm.completion`` so NO real network call is ever made, and
disable mock mode so the real ``_call_llm`` path is exercised.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.llm import service as svc
from app.llm.service import _call_llm, _parse_completion


def _fake_completion_response(content: str):
    """Build an object shaped like a LiteLLM completion response."""
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def test_parse_valid_json_with_trade():
    content = (
        '{"message": "Buying AAPL", '
        '"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 3}], '
        '"watchlist_changes": []}'
    )
    resp = _parse_completion(_fake_completion_response(content))
    assert resp.message == "Buying AAPL"
    assert len(resp.trades) == 1
    assert resp.trades[0].ticker == "AAPL"
    assert resp.trades[0].quantity == 3


def test_parse_valid_json_message_only():
    content = '{"message": "All good."}'
    resp = _parse_completion(_fake_completion_response(content))
    assert resp.message == "All good."
    assert resp.trades == []
    assert resp.watchlist_changes == []


def test_parse_malformed_json_falls_back():
    resp = _parse_completion(_fake_completion_response("not json at all {{{"))
    assert "trouble" in resp.message.lower()
    assert resp.trades == []


def test_parse_empty_content_falls_back():
    resp = _parse_completion(_fake_completion_response(""))
    assert resp.message
    assert resp.trades == []


def test_parse_unexpected_shape_falls_back():
    resp = _parse_completion(SimpleNamespace(choices=[]))
    assert resp.message
    assert resp.trades == []


def test_call_llm_uses_patched_completion(monkeypatch):
    """_call_llm should parse a (patched) completion without any network."""
    content = '{"message": "Hello from fake LLM", "trades": [], "watchlist_changes": []}'

    def fake_completion(*args, **kwargs):
        assert kwargs["model"] == svc.MODEL
        assert kwargs["response_format"] is not None
        return _fake_completion_response(content)

    monkeypatch.setattr("litellm.completion", fake_completion)
    resp = _call_llm([{"role": "user", "content": "hi"}])
    assert resp.message == "Hello from fake LLM"


def test_call_llm_handles_exception(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("litellm.completion", boom)
    resp = _call_llm([{"role": "user", "content": "hi"}])
    assert resp.message  # safe fallback, no crash
    assert resp.trades == []


@pytest.mark.asyncio
async def test_chat_real_path_with_patched_completion(conn, cache, source, monkeypatch):
    """End-to-end chat through the non-mock path with patched completion."""
    monkeypatch.setenv("LLM_MOCK", "false")
    content = (
        '{"message": "Executing", '
        '"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 2}], '
        '"watchlist_changes": []}'
    )

    def fake_completion(*args, **kwargs):
        return _fake_completion_response(content)

    monkeypatch.setattr("litellm.completion", fake_completion)

    result = await svc.chat(conn, cache, source, "please buy 2 AAPL")
    assert result["message"] == "Executing"
    assert result["trades"][0]["status"] == "executed"
    assert result["trades"][0]["price"] == 190.0
