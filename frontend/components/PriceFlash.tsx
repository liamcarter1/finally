'use client';

import { useEffect, useRef, useState } from 'react';
import { formatPrice } from '@/lib/format';

interface PriceFlashProps {
  price: number | null;
  className?: string;
}

/**
 * Renders a price and briefly applies a green/red flash class when the value
 * changes (up -> flash-up, down -> flash-down). The class is removed after the
 * 500ms CSS animation so it can re-trigger on the next change.
 */
export default function PriceFlash({ price, className = '' }: PriceFlashProps) {
  const prevRef = useRef<number | null>(null);
  const [flash, setFlash] = useState<'' | 'flash-up' | 'flash-down'>('');

  useEffect(() => {
    if (price == null) return;
    const prev = prevRef.current;
    if (prev != null && price !== prev) {
      setFlash(price > prev ? 'flash-up' : 'flash-down');
      const id = setTimeout(() => setFlash(''), 500);
      prevRef.current = price;
      return () => clearTimeout(id);
    }
    prevRef.current = price;
  }, [price]);

  return (
    <span
      data-testid="price-flash"
      className={`inline-block rounded px-1 tabular-nums ${flash} ${className}`}
    >
      {formatPrice(price)}
    </span>
  );
}
