import { render, screen } from '@testing-library/react';
import PositionsTable from '@/components/PositionsTable';
import Header from '@/components/Header';
import type { Position } from '@/lib/types';

const positions: Position[] = [
  {
    ticker: 'AAPL',
    quantity: 10,
    avg_cost: 190,
    current_price: 195,
    market_value: 1950,
    unrealized_pnl: 50,
    change_percent: 2.63,
  },
  {
    ticker: 'TSLA',
    quantity: 5,
    avg_cost: 260,
    current_price: 250,
    market_value: 1250,
    unrealized_pnl: -50,
    change_percent: -3.85,
  },
];

describe('PositionsTable', () => {
  it('renders a row per position with computed fields', () => {
    render(<PositionsTable positions={positions} prices={{}} />);
    const aapl = screen.getByTestId('position-row-AAPL');
    expect(aapl).toHaveTextContent('AAPL');
    expect(aapl).toHaveTextContent('190.00'); // avg cost
    expect(aapl).toHaveTextContent('195.00'); // current price
    expect(aapl).toHaveTextContent('$1,950.00'); // market value
    expect(aapl).toHaveTextContent('+2.63%');
  });

  it('uses live price from the price map when available', () => {
    render(
      <PositionsTable
        positions={positions}
        prices={{
          AAPL: {
            ticker: 'AAPL',
            price: 200,
            previous_price: 195,
            timestamp: 0,
            change: 5,
            change_percent: 2.5,
            direction: 'up',
          },
        }}
      />,
    );
    expect(screen.getByTestId('position-row-AAPL')).toHaveTextContent('200.00');
  });

  it('colors profit green and loss red', () => {
    render(<PositionsTable positions={positions} prices={{}} />);
    const profit = screen.getByTestId('position-row-AAPL');
    const loss = screen.getByTestId('position-row-TSLA');
    expect(profit.querySelector('.text-up')).toBeTruthy();
    expect(loss.querySelector('.text-down')).toBeTruthy();
  });

  it('shows empty state with no positions', () => {
    render(<PositionsTable positions={[]} prices={{}} />);
    expect(screen.getByText('No open positions.')).toBeInTheDocument();
  });
});

describe('Header portfolio display', () => {
  it('renders total value, cash and P&L', () => {
    render(
      <Header
        totalValue={12500}
        cashBalance={5000}
        unrealizedPnl={250}
        status="connected"
      />,
    );
    expect(screen.getByTestId('header-total-value')).toHaveTextContent(
      '$12,500.00',
    );
    expect(screen.getByTestId('header-cash')).toHaveTextContent('$5,000.00');
    expect(screen.getByTestId('header-pnl')).toHaveTextContent('$250.00');
    expect(screen.getByTestId('connection-status')).toHaveAttribute(
      'data-status',
      'connected',
    );
  });
});
