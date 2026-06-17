'use client';

import type { SparkPoint } from '@/lib/usePriceStream';

interface SparklineProps {
  points: SparkPoint[];
  width?: number;
  height?: number;
}

/**
 * Lightweight inline SVG sparkline. Renders the price path accumulated from the
 * SSE stream since page load. Colored by net direction over the window.
 */
export default function Sparkline({
  points,
  width = 96,
  height = 28,
}: SparklineProps) {
  if (!points || points.length < 2) {
    return (
      <svg
        width={width}
        height={height}
        data-testid="sparkline-empty"
        role="img"
        aria-label="no data yet"
      />
    );
  }

  const prices = points.map((p) => p.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const n = points.length;

  const coords = points.map((p, i) => {
    const x = (i / (n - 1)) * (width - 2) + 1;
    const y = height - 1 - ((p.price - min) / range) * (height - 2);
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });

  const rising = prices[n - 1] >= prices[0];
  const stroke = rising ? '#16c784' : '#ea3943';

  return (
    <svg
      width={width}
      height={height}
      data-testid="sparkline"
      role="img"
      aria-label="price sparkline"
      className="overflow-visible"
    >
      <polyline
        points={coords.join(' ')}
        fill="none"
        stroke={stroke}
        strokeWidth={1.25}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
