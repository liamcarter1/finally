'use client';

import { useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '@/lib/types';
import { formatPrice } from '@/lib/format';

interface ChatPanelProps {
  messages: ChatMessage[];
  loading: boolean;
  collapsed: boolean;
  onToggle: () => void;
  onSend: (message: string) => Promise<void> | void;
}

export default function ChatPanel({
  messages,
  loading,
  collapsed,
  onToggle,
  onSend,
}: ChatPanelProps) {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el && typeof el.scrollTo === 'function') {
      el.scrollTo({ top: el.scrollHeight });
    } else if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, loading]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    await onSend(text);
  };

  if (collapsed) {
    return (
      <button
        onClick={onToggle}
        data-testid="chat-toggle"
        aria-label="Open AI assistant"
        className="flex h-full w-10 flex-col items-center justify-center border-l border-border bg-bg-elevated text-xs"
        style={{ backgroundColor: '#1a1a2e' }}
      >
        <span className="rotate-180 text-accent [writing-mode:vertical-rl]">
          AI Assistant
        </span>
      </button>
    );
  }

  return (
    <aside
      className="flex h-full w-80 flex-col border-l border-border"
      style={{ backgroundColor: '#1a1a2e' }}
      aria-label="AI assistant"
    >
      <div className="flex items-center justify-between border-b border-border px-2 py-1">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-accent">
          AI Assistant
        </h2>
        <button
          onClick={onToggle}
          data-testid="chat-toggle"
          aria-label="Collapse assistant"
          className="text-flat hover:text-white"
        >
          ›
        </button>
      </div>

      <div
        ref={scrollRef}
        data-testid="chat-history"
        className="flex-1 space-y-2 overflow-y-auto p-2"
      >
        {messages.length === 0 && (
          <p className="text-xs text-flat">
            Ask FinAlly about your portfolio, request analysis, or have it trade
            for you.
          </p>
        )}
        {messages.map((m) => (
          <Message key={m.id} message={m} />
        ))}
        {loading && (
          <div
            data-testid="chat-loading"
            className="flex items-center gap-1 px-2 text-xs text-flat"
          >
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand [animation-delay:-0.2s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand [animation-delay:-0.1s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand" />
            <span className="ml-1">FinAlly is thinking…</span>
          </div>
        )}
      </div>

      <form onSubmit={submit} className="flex gap-1 border-t border-border p-2">
        <input
          aria-label="Message"
          placeholder="Ask FinAlly…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
          className="w-full rounded border border-border bg-bg px-2 py-1 text-xs outline-none focus:border-brand disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded px-3 py-1 text-xs font-semibold text-white disabled:opacity-50"
          style={{ backgroundColor: '#753991' }}
        >
          Send
        </button>
      </form>
    </aside>
  );
}

function Message({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  return (
    <div
      data-testid={`chat-message-${message.role}`}
      className={`max-w-[90%] rounded px-2 py-1 text-xs ${
        isUser
          ? 'ml-auto bg-brand/20 text-white'
          : 'mr-auto bg-bg-elevated text-gray-200'
      }`}
    >
      <p className="whitespace-pre-wrap">{message.content}</p>

      {message.trades && message.trades.length > 0 && (
        <ul className="mt-1 space-y-0.5 border-t border-border pt-1">
          {message.trades.map((t, i) => (
            <li
              key={i}
              data-testid="chat-trade-confirmation"
              className={t.status === 'executed' ? 'text-up' : 'text-down'}
            >
              {t.status === 'executed'
                ? `✓ ${t.side.toUpperCase()} ${t.quantity} ${t.ticker} @ ${formatPrice(
                    t.price,
                  )}`
                : `✗ ${t.side.toUpperCase()} ${t.quantity} ${t.ticker} — ${
                    t.error ?? 'failed'
                  }`}
            </li>
          ))}
        </ul>
      )}

      {message.watchlist_changes && message.watchlist_changes.length > 0 && (
        <ul className="mt-1 space-y-0.5 border-t border-border pt-1">
          {message.watchlist_changes.map((c, i) => (
            <li
              key={i}
              data-testid="chat-watchlist-confirmation"
              className={c.status === 'applied' ? 'text-brand' : 'text-down'}
            >
              {c.status === 'applied'
                ? `✓ ${c.action === 'add' ? 'Added' : 'Removed'} ${c.ticker}`
                : `✗ ${c.action} ${c.ticker} — ${c.error ?? 'failed'}`}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
