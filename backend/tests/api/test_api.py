"""API-level tests using FastAPI TestClient with overridden dependencies."""

from __future__ import annotations


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_portfolio_empty(client):
    resp = client.get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cash_balance"] == 10000.0
    assert body["positions"] == []
    assert body["total_value"] == 10000.0


def test_trade_buy_success(client):
    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["trade"]["ticker"] == "AAPL"
    assert body["trade"]["quantity"] == 5
    assert body["portfolio"]["cash_balance"] == 10000.0 - 5 * 190.0
    assert len(body["portfolio"]["positions"]) == 1


def test_trade_insufficient_cash_400(client):
    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "NFLX", "quantity": 1000, "side": "buy"},
    )
    assert resp.status_code == 400
    assert "Insufficient cash" in resp.json()["detail"]


def test_trade_unknown_price_400(client):
    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"},
    )
    assert resp.status_code == 400
    assert "No price available" in resp.json()["detail"]


def test_trade_invalid_quantity_422(client):
    # quantity must be > 0; pydantic rejects with 422 before reaching service.
    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 0, "side": "buy"},
    )
    assert resp.status_code == 422


def test_trade_invalid_side_422(client):
    resp = client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1, "side": "hold"},
    )
    assert resp.status_code == 422


def test_portfolio_history(client):
    client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1, "side": "buy"},
    )
    resp = client.get("/api/portfolio/history")
    assert resp.status_code == 200
    snaps = resp.json()["snapshots"]
    assert len(snaps) >= 1
    assert "total_value" in snaps[0]
    assert "recorded_at" in snaps[0]


def test_watchlist_get(client):
    resp = client.get("/api/watchlist")
    assert resp.status_code == 200
    wl = resp.json()["watchlist"]
    tickers = {r["ticker"] for r in wl}
    assert "AAPL" in tickers
    assert len(wl) == 10


def test_watchlist_add(client, source):
    resp = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert resp.status_code == 200
    tickers = {r["ticker"] for r in resp.json()["watchlist"]}
    assert "PYPL" in tickers
    assert "PYPL" in source.added


def test_watchlist_add_duplicate_400(client):
    resp = client.post("/api/watchlist", json={"ticker": "AAPL"})
    assert resp.status_code == 400
    assert "already" in resp.json()["detail"]


def test_watchlist_delete(client, source):
    resp = client.delete("/api/watchlist/AAPL")
    assert resp.status_code == 200
    tickers = {r["ticker"] for r in resp.json()["watchlist"]}
    assert "AAPL" not in tickers
    assert "AAPL" in source.removed
