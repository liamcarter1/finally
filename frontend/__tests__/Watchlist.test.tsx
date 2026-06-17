import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Watchlist from '@/components/Watchlist';
import type { WatchlistEntry } from '@/lib/types';

const entries: WatchlistEntry[] = [
  {
    ticker: 'AAPL',
    price: 195,
    previous_price: 194,
    change: 1,
    change_percent: 0.51,
    direction: 'up',
  },
  {
    ticker: 'TSLA',
    price: 250,
    previous_price: 255,
    change: -5,
    change_percent: -1.96,
    direction: 'down',
  },
];

describe('Watchlist', () => {
  it('renders rows for each ticker', () => {
    render(
      <Watchlist
        entries={entries}
        prices={{}}
        history={{}}
        selected={null}
        onSelect={jest.fn()}
        onAdd={jest.fn()}
        onRemove={jest.fn()}
      />,
    );
    expect(screen.getByTestId('watchlist-row-AAPL')).toBeInTheDocument();
    expect(screen.getByTestId('watchlist-row-TSLA')).toBeInTheDocument();
    expect(screen.getByText('+0.51%')).toBeInTheDocument();
    expect(screen.getByText('-1.96%')).toBeInTheDocument();
  });

  it('calls onSelect when a row is clicked', () => {
    const onSelect = jest.fn();
    render(
      <Watchlist
        entries={entries}
        prices={{}}
        history={{}}
        selected={null}
        onSelect={onSelect}
        onAdd={jest.fn()}
        onRemove={jest.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId('watchlist-row-TSLA'));
    expect(onSelect).toHaveBeenCalledWith('TSLA');
  });

  it('adds a ticker via the form (uppercased)', async () => {
    const onAdd = jest.fn().mockResolvedValue(undefined);
    render(
      <Watchlist
        entries={entries}
        prices={{}}
        history={{}}
        selected={null}
        onSelect={jest.fn()}
        onAdd={onAdd}
        onRemove={jest.fn()}
      />,
    );
    await userEvent.type(screen.getByLabelText('Add ticker'), 'nvda');
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    await waitFor(() => expect(onAdd).toHaveBeenCalledWith('NVDA'));
  });

  it('removes a ticker via the remove button', () => {
    const onRemove = jest.fn();
    render(
      <Watchlist
        entries={entries}
        prices={{}}
        history={{}}
        selected={null}
        onSelect={jest.fn()}
        onAdd={jest.fn()}
        onRemove={onRemove}
      />,
    );
    fireEvent.click(screen.getByLabelText('Remove AAPL'));
    expect(onRemove).toHaveBeenCalledWith('AAPL');
  });

  it('shows an error if add fails', async () => {
    const onAdd = jest.fn().mockRejectedValue(new Error('Invalid ticker'));
    render(
      <Watchlist
        entries={entries}
        prices={{}}
        history={{}}
        selected={null}
        onSelect={jest.fn()}
        onAdd={onAdd}
        onRemove={jest.fn()}
      />,
    );
    await userEvent.type(screen.getByLabelText('Add ticker'), 'ZZZZ');
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid ticker');
  });
});
