'use client';

import type { PriceMap, Position } from '@/lib/types';
import {
  formatCurrency,
  formatPercent,
  formatPrice,
  formatQty,
  pnlColorClass,
} from '@/lib/format';

interface PositionsTableProps {
  positions: Position[];
  prices: PriceMap;
  onSelect?: (ticker: string) => void;
}

export default function PositionsTable({
  positions,
  prices,
  onSelect,
}: PositionsTableProps) {
  return (
    <section className="flex h-full flex-col" aria-label="Positions">
      <h2 className="border-b border-border bg-bg-elevated px-2 py-1 text-xs font-semibold uppercase tracking-wider text-accent">
        Positions
      </h2>
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs" data-testid="positions-table">
          <thead className="sticky top-0 bg-bg-panel text-left text-[10px] uppercase tracking-wider text-flat">
            <tr>
              <th className="px-2 py-1">Sym</th>
              <th className="px-2 py-1 text-right">Qty</th>
              <th className="px-2 py-1 text-right">Avg Cost</th>
              <th className="px-2 py-1 text-right">Price</th>
              <th className="px-2 py-1 text-right">Mkt Val</th>
              <th className="px-2 py-1 text-right">Unreal P&L</th>
              <th className="px-2 py-1 text-right">% Chg</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => {
              const live = prices[p.ticker]?.price ?? p.current_price;
              return (
                <tr
                  key={p.ticker}
                  data-testid={`position-row-${p.ticker}`}
                  onClick={() => onSelect?.(p.ticker)}
                  className="cursor-pointer border-b border-border-muted hover:bg-bg-elevated"
                >
                  <td className="px-2 py-1 font-semibold text-white">
                    {p.ticker}
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums">
                    {formatQty(p.quantity)}
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums">
                    {formatPrice(p.avg_cost)}
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums">
                    {formatPrice(live)}
                  </td>
                  <td className="px-2 py-1 text-right tabular-nums">
                    {formatCurrency(p.market_value)}
                  </td>
                  <td
                    className={`px-2 py-1 text-right tabular-nums ${pnlColorClass(
                      p.unrealized_pnl,
                    )}`}
                  >
                    {formatCurrency(p.unrealized_pnl)}
                  </td>
                  <td
                    className={`px-2 py-1 text-right tabular-nums ${pnlColorClass(
                      p.change_percent,
                    )}`}
                  >
                    {formatPercent(p.change_percent)}
                  </td>
                </tr>
              );
            })}
            {positions.length === 0 && (
              <tr>
                <td colSpan={7} className="px-2 py-4 text-center text-flat">
                  No open positions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
