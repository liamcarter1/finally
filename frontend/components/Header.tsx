'use client';

import type { ConnectionStatus } from '@/lib/types';
import { formatCurrency, pnlColorClass } from '@/lib/format';
import ConnectionDot from './ConnectionDot';

interface HeaderProps {
  totalValue: number | null;
  cashBalance: number | null;
  unrealizedPnl: number | null;
  status: ConnectionStatus;
}

export default function Header({
  totalValue,
  cashBalance,
  unrealizedPnl,
  status,
}: HeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-border bg-bg-elevated px-4 py-2">
      <div className="flex items-center gap-2">
        <span className="text-lg font-bold tracking-tight text-accent">
          Fin<span className="text-brand">Ally</span>
        </span>
        <span className="hidden text-xs text-flat sm:inline">
          AI Trading Workstation
        </span>
      </div>

      <div className="flex items-center gap-6">
        <Stat label="Total Value" data-testid="header-total-value">
          <span className="text-base font-semibold text-white tabular-nums">
            {formatCurrency(totalValue)}
          </span>
        </Stat>
        <Stat label="Cash" data-testid="header-cash">
          <span className="text-base font-semibold text-white tabular-nums">
            {formatCurrency(cashBalance)}
          </span>
        </Stat>
        <Stat label="Unrealized P&L" data-testid="header-pnl">
          <span
            className={`text-base font-semibold tabular-nums ${pnlColorClass(
              unrealizedPnl,
            )}`}
          >
            {formatCurrency(unrealizedPnl)}
          </span>
        </Stat>
        <ConnectionDot status={status} />
      </div>
    </header>
  );
}

function Stat({
  label,
  children,
  ...rest
}: {
  label: string;
  children: React.ReactNode;
  'data-testid'?: string;
}) {
  return (
    <div className="flex flex-col items-end leading-tight" {...rest}>
      <span className="text-[10px] uppercase tracking-wider text-flat">
        {label}
      </span>
      {children}
    </div>
  );
}
