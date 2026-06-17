'use client';

import { useState } from 'react';
import type { PriceMap, WatchlistEntry } from '@/lib/types';
import type { SparkPoint } from '@/lib/usePriceStream';
import { formatPercent, pnlColorClass } from '@/lib/format';
import PriceFlash from './PriceFlash';
import Sparkline from './Sparkline';

interface WatchlistProps {
  entries: WatchlistEntry[];
  prices: PriceMap;
  history: Record<string, SparkPoint[]>;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => Promise<void> | void;
  onRemove: (ticker: string) => Promise<void> | void;
}

export default function Watchlist({
  entries,
  prices,
  history,
  selected,
  onSelect,
  onAdd,
  onRemove,
}: WatchlistProps) {
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submitAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const ticker = input.trim().toUpperCase();
    if (!ticker) return;
    setBusy(true);
    setError(null);
    try {
      await onAdd(ticker);
      setInput('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="flex h-full flex-col" aria-label="Watchlist">
      <PanelTitle>Watchlist</PanelTitle>

      <form onSubmit={submitAdd} className="flex gap-1 px-2 py-2">
        <input
          aria-label="Add ticker"
          placeholder="Add ticker…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="w-full rounded border border-border bg-bg px-2 py-1 text-xs uppercase outline-none focus:border-brand"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded bg-brand px-2 py-1 text-xs font-semibold text-white disabled:opacity-50"
        >
          Add
        </button>
      </form>
      {error && (
        <p className="px-2 pb-1 text-xs text-down" role="alert">
          {error}
        </p>
      )}

      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-bg-panel text-left text-[10px] uppercase tracking-wider text-flat">
            <tr>
              <th className="px-2 py-1">Sym</th>
              <th className="px-2 py-1 text-right">Price</th>
              <th className="px-2 py-1 text-right">Chg%</th>
              <th className="px-2 py-1 text-center">Trend</th>
              <th className="px-1 py-1" />
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => {
              const live = prices[entry.ticker];
              const price = live?.price ?? entry.price ?? null;
              const changePct =
                live?.change_percent ?? entry.change_percent ?? null;
              const isSelected = selected === entry.ticker;
              return (
                <tr
                  key={entry.ticker}
                  data-testid={`watchlist-row-${entry.ticker}`}
                  onClick={() => onSelect(entry.ticker)}
                  className={`cursor-pointer border-b border-border-muted hover:bg-bg-elevated ${
                    isSelected ? 'bg-bg-elevated' : ''
                  }`}
                >
                  <td className="px-2 py-1 font-semibold text-white">
                    {entry.ticker}
                  </td>
                  <td className="px-2 py-1 text-right">
                    <PriceFlash price={price} />
                  </td>
                  <td
                    className={`px-2 py-1 text-right tabular-nums ${pnlColorClass(
                      changePct,
                    )}`}
                  >
                    {formatPercent(changePct)}
                  </td>
                  <td className="px-2 py-1">
                    <div className="flex justify-center">
                      <Sparkline points={history[entry.ticker] ?? []} />
                    </div>
                  </td>
                  <td className="px-1 py-1 text-right">
                    <button
                      aria-label={`Remove ${entry.ticker}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        void onRemove(entry.ticker);
                      }}
                      className="text-flat hover:text-down"
                    >
                      ×
                    </button>
                  </td>
                </tr>
              );
            })}
            {entries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-2 py-4 text-center text-flat">
                  No tickers. Add one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PanelTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="border-b border-border bg-bg-elevated px-2 py-1 text-xs font-semibold uppercase tracking-wider text-accent">
      {children}
    </h2>
  );
}
