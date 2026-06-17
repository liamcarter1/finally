import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatPanel from '@/components/ChatPanel';
import type { ChatMessage } from '@/lib/types';

const baseProps = {
  collapsed: false,
  onToggle: jest.fn(),
  onSend: jest.fn().mockResolvedValue(undefined),
};

describe('ChatPanel', () => {
  it('renders user and assistant messages', () => {
    const messages: ChatMessage[] = [
      { id: '1', role: 'user', content: 'How is my portfolio?' },
      { id: '2', role: 'assistant', content: 'It looks balanced.' },
    ];
    render(<ChatPanel {...baseProps} messages={messages} loading={false} />);
    expect(screen.getByText('How is my portfolio?')).toBeInTheDocument();
    expect(screen.getByText('It looks balanced.')).toBeInTheDocument();
  });

  it('shows loading indicator when awaiting a response', () => {
    render(<ChatPanel {...baseProps} messages={[]} loading={true} />);
    expect(screen.getByTestId('chat-loading')).toBeInTheDocument();
  });

  it('renders inline trade confirmations', () => {
    const messages: ChatMessage[] = [
      {
        id: '1',
        role: 'assistant',
        content: 'Bought it.',
        trades: [
          {
            ticker: 'AAPL',
            side: 'buy',
            quantity: 10,
            price: 195,
            status: 'executed',
          },
        ],
      },
    ];
    render(<ChatPanel {...baseProps} messages={messages} loading={false} />);
    const conf = screen.getByTestId('chat-trade-confirmation');
    expect(conf).toHaveTextContent('BUY 10 AAPL');
    expect(conf.className).toContain('text-up');
  });

  it('renders a failed trade confirmation with error', () => {
    const messages: ChatMessage[] = [
      {
        id: '1',
        role: 'assistant',
        content: 'Could not trade.',
        trades: [
          {
            ticker: 'AAPL',
            side: 'buy',
            quantity: 10000,
            price: 195,
            status: 'rejected',
            error: 'Insufficient cash',
          },
        ],
      },
    ];
    render(<ChatPanel {...baseProps} messages={messages} loading={false} />);
    expect(screen.getByTestId('chat-trade-confirmation')).toHaveTextContent(
      'Insufficient cash',
    );
  });

  it('renders a successful watchlist change as a success confirmation', () => {
    const messages: ChatMessage[] = [
      {
        id: '1',
        role: 'assistant',
        content: 'Added it.',
        watchlist_changes: [
          { ticker: 'PYPL', action: 'add', status: 'applied' },
        ],
      },
    ];
    render(<ChatPanel {...baseProps} messages={messages} loading={false} />);
    const conf = screen.getByTestId('chat-watchlist-confirmation');
    expect(conf).toHaveTextContent('Added PYPL');
    // Success branch: green/brand styling with a check, not the red failure branch.
    expect(conf).toHaveTextContent('✓');
    expect(conf.className).toContain('text-brand');
    expect(conf.className).not.toContain('text-down');
  });

  it('renders a failed watchlist change as a failure confirmation', () => {
    const messages: ChatMessage[] = [
      {
        id: '1',
        role: 'assistant',
        content: 'Could not add it.',
        watchlist_changes: [
          {
            ticker: 'PYPL',
            action: 'add',
            status: 'failed',
            error: 'unknown ticker',
          },
        ],
      },
    ];
    render(<ChatPanel {...baseProps} messages={messages} loading={false} />);
    const conf = screen.getByTestId('chat-watchlist-confirmation');
    expect(conf).toHaveTextContent('unknown ticker');
    expect(conf.className).toContain('text-down');
  });

  it('sends a message on submit', async () => {
    const onSend = jest.fn().mockResolvedValue(undefined);
    render(
      <ChatPanel {...baseProps} onSend={onSend} messages={[]} loading={false} />,
    );
    await userEvent.type(screen.getByLabelText('Message'), 'buy 5 AAPL');
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    await waitFor(() => expect(onSend).toHaveBeenCalledWith('buy 5 AAPL'));
  });

  it('collapses to a toggle button when collapsed', () => {
    render(
      <ChatPanel {...baseProps} collapsed messages={[]} loading={false} />,
    );
    expect(screen.getByTestId('chat-toggle')).toBeInTheDocument();
    expect(screen.queryByLabelText('Message')).not.toBeInTheDocument();
  });
});
