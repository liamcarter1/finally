'use client';

import {
  ResponsiveContainer,
  Tooltip,
  Treemap,
} from 'recharts';
import type { Position } from '@/lib/types';
import { formatCurrency, formatPercent } from '@/lib/format';

interface HeatmapProps {
  positions: Position[];
}

/** Map P&L percent to a green/red fill. */
function pnlFill(changePercent: number): string {
  if (changePercent > 0) return '#16794f';
  if (changePercent < 0) return '#9b2c34';
  return '#2a2f3a';
}

interface TreemapNode {
  name: string;
  size: number;
  changePercent: number;
  pnl: number;
}

// Recharts passes geometry + datum props into the content renderer.
function HeatCell(props: Record<string, unknown>) {
  const x = props.x as number;
  const y = props.y as number;
  const width = props.width as number;
  const height = props.height as number;
  const name = props.name as string | undefined;
  const changePercent = (props.changePercent as number) ?? 0;
  if (width <= 0 || height <= 0) return null;
  const showLabel = width > 44 && height > 24;
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{ fill: pnlFill(changePercent), stroke: '#0d1117', strokeWidth: 2 }}
      />
      {showLabel && name && (
        <>
          <text
            x={x + 6}
            y={y + 16}
            fill="#fff"
            fontSize={12}
            fontWeight={600}
          >
            {name}
          </text>
          <text x={x + 6} y={y + 30} fill="#d0d7de" fontSize={10}>
            {formatPercent(changePercent)}
          </text>
        </>
      )}
    </g>
  );
}

export default function Heatmap({ positions }: HeatmapProps) {
  const data: TreemapNode[] = positions
    .filter((p) => p.market_value > 0)
    .map((p) => ({
      name: p.ticker,
      size: p.market_value,
      changePercent: p.change_percent,
      pnl: p.unrealized_pnl,
    }));

  return (
    <section className="flex h-full flex-col" aria-label="Portfolio heatmap">
      <h2 className="border-b border-border bg-bg-elevated px-2 py-1 text-xs font-semibold uppercase tracking-wider text-accent">
        Allocation Heatmap
      </h2>
      <div className="flex-1 p-2" data-testid="heatmap">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-flat">
            No positions yet.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={data}
              dataKey="size"
              nameKey="name"
              stroke="#0d1117"
              isAnimationActive={false}
              content={<HeatCell />}
            >
              <Tooltip
                contentStyle={{
                  background: '#161b22',
                  border: '1px solid #2a2f3a',
                  fontSize: 12,
                }}
                formatter={(value, _name, item) => {
                  const node = item?.payload as TreemapNode | undefined;
                  return [
                    `${formatCurrency(value as number)} (${formatPercent(
                      node?.changePercent ?? 0,
                    )})`,
                    node?.name ?? '',
                  ];
                }}
              />
            </Treemap>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
