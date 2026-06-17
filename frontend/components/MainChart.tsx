'use client';

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { SparkPoint } from '@/lib/usePriceStream';
import { formatPrice } from '@/lib/format';

interface MainChartProps {
  ticker: string | null;
  points: SparkPoint[];
}

export default function MainChart({ ticker, points }: MainChartProps) {
  const data = points.map((p) => ({
    time: new Date(p.t * 1000).toLocaleTimeString(),
    price: p.price,
  }));

  return (
    <section className="flex h-full flex-col" aria-label="Price chart">
      <h2 className="flex items-center gap-2 border-b border-border bg-bg-elevated px-2 py-1 text-xs font-semibold uppercase tracking-wider text-accent">
        Chart
        {ticker && <span className="text-white">· {ticker}</span>}
      </h2>
      <div className="flex-1 p-2" data-testid="main-chart">
        {data.length < 2 ? (
          <div className="flex h-full items-center justify-center text-xs text-flat">
            {ticker
              ? 'Accumulating live data…'
              : 'Select a ticker from the watchlist.'}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="priceFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#209dd7" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#209dd7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="time"
                tick={{ fill: '#8b949e', fontSize: 10 }}
                minTickGap={40}
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{ fill: '#8b949e', fontSize: 10 }}
                width={56}
                tickFormatter={(v) => formatPrice(v as number)}
              />
              <Tooltip
                contentStyle={{
                  background: '#161b22',
                  border: '1px solid #2a2f3a',
                  fontSize: 12,
                }}
                labelStyle={{ color: '#8b949e' }}
                formatter={(v) => [formatPrice(v as number), 'Price']}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke="#209dd7"
                strokeWidth={1.5}
                fill="url(#priceFill)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
