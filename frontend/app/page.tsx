'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { usePriceStream } from '@/lib/usePriceStream';
import type {
  ChatMessage,
  Portfolio,
  PortfolioSnapshot,
  TradeSide,
  WatchlistEntry,
} from '@/lib/types';
import Header from '@/components/Header';
import Watchlist from '@/components/Watchlist';
import MainChart from '@/components/MainChart';
import Heatmap from '@/components/Heatmap';
import PnlChart from '@/components/PnlChart';
import PositionsTable from '@/components/PositionsTable';
import TradeBar from '@/components/TradeBar';
import ChatPanel from '@/components/ChatPanel';

export default function Page() {
  const { prices, history, status } = usePriceStream();

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatCollapsed, setChatCollapsed] = useState(false);

  const refreshPortfolio = useCallback(async () => {
    try {
      setPortfolio(await api.getPortfolio());
    } catch {
      /* keep last known */
    }
  }, []);

  const refreshWatchlist = useCallback(async () => {
    try {
      const res = await api.getWatchlist();
      setWatchlist(res.watchlist);
      setSelected((cur) => cur ?? res.watchlist[0]?.ticker ?? null);
    } catch {
      /* keep last known */
    }
  }, []);

  const refreshHistory = useCallback(async () => {
    try {
      const res = await api.getPortfolioHistory();
      setSnapshots(res.snapshots);
    } catch {
      /* keep last known */
    }
  }, []);

  // Initial load + periodic refresh of portfolio/history.
  useEffect(() => {
    void refreshPortfolio();
    void refreshWatchlist();
    void refreshHistory();
    const id = setInterval(() => {
      void refreshPortfolio();
      void refreshHistory();
    }, 15000);
    return () => clearInterval(id);
  }, [refreshPortfolio, refreshWatchlist, refreshHistory]);

  const handleTrade = useCallback(
    async (ticker: string, quantity: number, side: TradeSide) => {
      const res = await api.trade(ticker, quantity, side);
      setPortfolio(res.portfolio);
      void refreshHistory();
    },
    [refreshHistory],
  );

  const handleAdd = useCallback(async (ticker: string) => {
    const res = await api.addWatchlist(ticker);
    setWatchlist(res.watchlist);
  }, []);

  const handleRemove = useCallback(
    async (ticker: string) => {
      const res = await api.removeWatchlist(ticker);
      setWatchlist(res.watchlist);
      setSelected((cur) =>
        cur === ticker ? res.watchlist[0]?.ticker ?? null : cur,
      );
    },
    [],
  );

  const handleSend = useCallback(
    async (message: string) => {
      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: 'user',
        content: message,
      };
      setChatMessages((prev) => [...prev, userMsg]);
      setChatLoading(true);
      try {
        const res = await api.chat(message);
        setChatMessages((prev) => [
          ...prev,
          {
            id: `a-${Date.now()}`,
            role: 'assistant',
            content: res.message,
            trades: res.trades,
            watchlist_changes: res.watchlist_changes,
          },
        ]);
        // The AI may have traded / changed the watchlist — refresh state.
        if (res.trades.length > 0) {
          void refreshPortfolio();
          void refreshHistory();
        }
        if (res.watchlist_changes.length > 0) void refreshWatchlist();
      } catch (err) {
        setChatMessages((prev) => [
          ...prev,
          {
            id: `e-${Date.now()}`,
            role: 'assistant',
            content:
              err instanceof Error
                ? `Error: ${err.message}`
                : 'Something went wrong.',
          },
        ]);
      } finally {
        setChatLoading(false);
      }
    },
    [refreshPortfolio, refreshHistory, refreshWatchlist],
  );

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-bg text-gray-200">
      <Header
        totalValue={portfolio?.total_value ?? null}
        cashBalance={portfolio?.cash_balance ?? null}
        unrealizedPnl={portfolio?.unrealized_pnl ?? null}
        status={status}
      />

      <div className="flex flex-1 overflow-hidden">
        {/* Left: watchlist */}
        <div className="w-72 shrink-0 border-r border-border bg-bg-panel">
          <Watchlist
            entries={watchlist}
            prices={prices}
            history={history}
            selected={selected}
            onSelect={setSelected}
            onAdd={handleAdd}
            onRemove={handleRemove}
          />
        </div>

        {/* Center: charts + positions */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="grid flex-1 grid-cols-2 gap-px overflow-hidden bg-border">
            <div className="bg-bg-panel">
              <MainChart
                ticker={selected}
                points={selected ? history[selected] ?? [] : []}
              />
            </div>
            <div className="bg-bg-panel">
              <PnlChart snapshots={snapshots} />
            </div>
            <div className="bg-bg-panel">
              <Heatmap positions={portfolio?.positions ?? []} />
            </div>
            <div className="overflow-hidden bg-bg-panel">
              <PositionsTable
                positions={portfolio?.positions ?? []}
                prices={prices}
                onSelect={setSelected}
              />
            </div>
          </div>
          <TradeBar defaultTicker={selected} onTrade={handleTrade} />
        </div>

        {/* Right: AI chat */}
        <ChatPanel
          messages={chatMessages}
          loading={chatLoading}
          collapsed={chatCollapsed}
          onToggle={() => setChatCollapsed((c) => !c)}
          onSend={handleSend}
        />
      </div>
    </div>
  );
}
