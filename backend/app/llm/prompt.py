"""System prompt and portfolio-context construction for the chat assistant.

Per PLAN.md §9, the model is prompted as "FinAlly, an AI trading assistant"
and is given a compact, data-driven snapshot of the user's portfolio and
watchlist (with live prices) before each turn.
"""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You are FinAlly, an AI trading assistant embedded in a simulated trading "
    "workstation. You help the user manage a virtual portfolio of US equities.\n\n"
    "Your responsibilities:\n"
    "- Analyze portfolio composition, risk concentration, and unrealized P&L.\n"
    "- Suggest trades with clear, data-driven reasoning.\n"
    "- Execute trades when the user asks or agrees (this is a simulation with "
    "fake money, so execution is automatic and requires no confirmation).\n"
    "- Manage the watchlist proactively (add/remove tickers).\n"
    "- Be concise and data-driven; reference the user's actual numbers.\n\n"
    "Rules:\n"
    "- You always respond with valid structured JSON matching the required "
    "schema: an object with `message` (string), `trades` (array of "
    "{ticker, side, quantity}), and `watchlist_changes` (array of "
    "{ticker, action}). Use empty arrays when there are no actions.\n"
    "- `side` is 'buy' or 'sell'; `action` is 'add' or 'remove'.\n"
    "- Only emit a trade when the user clearly wants it executed. Each trade is "
    "validated like a manual order (sufficient cash for buys, sufficient shares "
    "for sells); if one fails, you will be told and should relay it to the user.\n"
    "- Quantities are share counts (fractional allowed) and must be positive.\n"
    "- Put your conversational reply in `message`; never leave it empty."
)


def build_context_block(portfolio: dict, watchlist: list[dict]) -> str:
    """Render a compact, human-readable portfolio + watchlist context block.

    This becomes a system message appended after the main system prompt so the
    model can ground its analysis in the user's current state.
    """
    lines: list[str] = ["CURRENT PORTFOLIO SNAPSHOT"]
    lines.append(f"Cash balance: ${portfolio['cash_balance']:,.2f}")
    lines.append(f"Positions value: ${portfolio['positions_value']:,.2f}")
    lines.append(f"Total portfolio value: ${portfolio['total_value']:,.2f}")
    lines.append(f"Total unrealized P&L: ${portfolio['unrealized_pnl']:,.2f}")

    positions = portfolio.get("positions") or []
    if positions:
        lines.append("Positions:")
        for p in positions:
            lines.append(
                f"  {p['ticker']}: qty={p['quantity']:g} "
                f"avg_cost=${p['avg_cost']:,.2f} "
                f"price=${p['current_price']:,.2f} "
                f"value=${p['market_value']:,.2f} "
                f"pnl=${p['unrealized_pnl']:,.2f} "
                f"({p['change_percent']:+.2f}%)"
            )
    else:
        lines.append("Positions: none (all cash)")

    if watchlist:
        lines.append("Watchlist (live prices):")
        for w in watchlist:
            price = w.get("price")
            if price is None:
                lines.append(f"  {w['ticker']}: price unavailable")
            else:
                cp = w.get("change_percent")
                cp_str = f" ({cp:+.2f}%)" if cp is not None else ""
                lines.append(f"  {w['ticker']}: ${price:,.2f}{cp_str}")
    else:
        lines.append("Watchlist: empty")

    return "\n".join(lines)
