'use client';

import { useState, useEffect } from 'react';
import type { TradeSide } from '@/lib/types';

interface TradeBarProps {
  defaultTicker?: string | null;
  onTrade: (ticker: string, quantity: number, side: TradeSide) => Promise<void>;
}

export default function TradeBar({ defaultTicker, onTrade }: TradeBarProps) {
  const [ticker, setTicker] = useState(defaultTicker ?? '');
  const [qty, setQty] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ kind: 'ok' | 'err'; text: string } | null>(
    null,
  );

  // Follow watchlist selection unless the user has typed a custom symbol.
  useEffect(() => {
    if (defaultTicker) setTicker(defaultTicker);
  }, [defaultTicker]);

  const submit = async (side: TradeSide) => {
    const sym = ticker.trim().toUpperCase();
    const quantity = Number(qty);
    if (!sym || !Number.isFinite(quantity) || quantity <= 0) {
      setMsg({ kind: 'err', text: 'Enter a ticker and positive quantity.' });
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      await onTrade(sym, quantity, side);
      setMsg({ kind: 'ok', text: `${side.toUpperCase()} ${quantity} ${sym} filled.` });
      setQty('');
    } catch (err) {
      setMsg({
        kind: 'err',
        text: err instanceof Error ? err.message : 'Trade failed.',
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section
      className="flex items-center gap-2 border-t border-border bg-bg-elevated px-3 py-2"
      aria-label="Trade"
    >
      <span className="text-xs font-semibold uppercase tracking-wider text-accent">
        Trade
      </span>
      <input
        aria-label="Ticker"
        placeholder="TICKER"
        value={ticker}
        onChange={(e) => setTicker(e.target.value)}
        className="w-24 rounded border border-border bg-bg px-2 py-1 text-sm uppercase outline-none focus:border-brand"
      />
      <input
        aria-label="Quantity"
        placeholder="Qty"
        type="number"
        min="0"
        step="any"
        value={qty}
        onChange={(e) => setQty(e.target.value)}
        className="w-24 rounded border border-border bg-bg px-2 py-1 text-sm tabular-nums outline-none focus:border-brand"
      />
      <button
        type="button"
        disabled={busy}
        onClick={() => submit('buy')}
        className="rounded bg-up px-4 py-1 text-sm font-semibold text-white disabled:opacity-50"
      >
        Buy
      </button>
      <button
        type="button"
        disabled={busy}
        onClick={() => submit('sell')}
        className="rounded bg-down px-4 py-1 text-sm font-semibold text-white disabled:opacity-50"
      >
        Sell
      </button>
      {/* Purple submit accent per spec (#753991) */}
      <button
        type="button"
        disabled={busy}
        onClick={() => submit('buy')}
        className="rounded px-4 py-1 text-sm font-semibold text-white disabled:opacity-50"
        style={{ backgroundColor: '#753991' }}
        title="Submit market buy"
      >
        Submit
      </button>
      {msg && (
        <span
          role="status"
          className={`text-xs ${msg.kind === 'ok' ? 'text-up' : 'text-down'}`}
        >
          {msg.text}
        </span>
      )}
    </section>
  );
}
