'use client';

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { PortfolioSnapshot } from '@/lib/types';
import { formatCurrency } from '@/lib/format';

export default function PnlChart({
  snapshots,
}: {
  snapshots: PortfolioSnapshot[];
}) {
  const data = snapshots.map((s) => ({
    time: new Date(s.recorded_at).toLocaleTimeString(),
    value: s.total_value,
  }));

  return (
    <section className="flex h-full flex-col" aria-label="Portfolio value chart">
      <h2 className="border-b border-border bg-bg-elevated px-2 py-1 text-xs font-semibold uppercase tracking-wider text-accent">
        Portfolio Value
      </h2>
      <div className="flex-1 p-2" data-testid="pnl-chart">
        {data.length < 2 ? (
          <div className="flex h-full items-center justify-center text-xs text-flat">
            Collecting snapshots…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <XAxis
                dataKey="time"
                tick={{ fill: '#8b949e', fontSize: 10 }}
                minTickGap={40}
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#8b949e', fontSize: 10 }}
                width={64}
                tickFormatter={(v) => formatCurrency(v as number)}
              />
              <Tooltip
                contentStyle={{
                  background: '#161b22',
                  border: '1px solid #2a2f3a',
                  fontSize: 12,
                }}
                labelStyle={{ color: '#8b949e' }}
                formatter={(v) => [formatCurrency(v as number), 'Total']}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#ecad0a"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
