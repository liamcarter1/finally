'use client';

import type { ConnectionStatus } from '@/lib/types';

const CONFIG: Record<ConnectionStatus, { color: string; label: string }> = {
  connected: { color: 'bg-up', label: 'Connected' },
  reconnecting: { color: 'bg-accent', label: 'Reconnecting' },
  disconnected: { color: 'bg-down', label: 'Disconnected' },
};

export default function ConnectionDot({ status }: { status: ConnectionStatus }) {
  const { color, label } = CONFIG[status];
  return (
    <div
      className="flex items-center gap-2 text-xs text-flat"
      data-testid="connection-status"
      data-status={status}
      title={label}
    >
      <span
        className={`inline-block h-2.5 w-2.5 rounded-full ${color} ${
          status === 'reconnecting' ? 'animate-pulse' : ''
        }`}
        aria-hidden
      />
      <span>{label}</span>
    </div>
  );
}
