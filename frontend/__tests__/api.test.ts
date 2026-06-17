import { api, ApiError } from '@/lib/api';
import {
  formatCurrency,
  formatPercent,
  formatQty,
  pnlColorClass,
} from '@/lib/format';

describe('format helpers', () => {
  it('formats currency', () => {
    expect(formatCurrency(1234.5)).toBe('$1,234.50');
    expect(formatCurrency(null)).toBe('--');
  });
  it('formats percent with sign', () => {
    expect(formatPercent(2.5)).toBe('+2.50%');
    expect(formatPercent(-1.2)).toBe('-1.20%');
    expect(formatPercent(null)).toBe('--');
  });
  it('formats fractional quantities', () => {
    expect(formatQty(1.5)).toBe('1.5');
    expect(formatQty(10)).toBe('10');
  });
  it('chooses pnl color class', () => {
    expect(pnlColorClass(5)).toBe('text-up');
    expect(pnlColorClass(-5)).toBe('text-down');
    expect(pnlColorClass(0)).toBe('text-flat');
  });
});

describe('api client', () => {
  const mockFetch = jest.fn();

  beforeEach(() => {
    mockFetch.mockReset();
    // @ts-expect-error override global fetch in tests
    global.fetch = mockFetch;
  });

  function ok(body: unknown) {
    return Promise.resolve({
      ok: true,
      status: 200,
      text: () => Promise.resolve(JSON.stringify(body)),
    });
  }

  it('GET /api/portfolio uses relative path', async () => {
    mockFetch.mockReturnValue(ok({ total_value: 10000 }));
    const res = await api.getPortfolio();
    expect(mockFetch).toHaveBeenCalledWith('/api/portfolio', expect.anything());
    expect(res.total_value).toBe(10000);
  });

  it('POST /api/portfolio/trade sends the trade body', async () => {
    mockFetch.mockReturnValue(ok({ trade: {}, portfolio: {} }));
    await api.trade('AAPL', 10, 'buy');
    const [url, init] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/portfolio/trade');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({
      ticker: 'AAPL',
      quantity: 10,
      side: 'buy',
    });
  });

  it('DELETE /api/watchlist/{ticker} encodes ticker', async () => {
    mockFetch.mockReturnValue(ok({ watchlist: [] }));
    await api.removeWatchlist('AAPL');
    expect(mockFetch.mock.calls[0][0]).toBe('/api/watchlist/AAPL');
    expect(mockFetch.mock.calls[0][1].method).toBe('DELETE');
  });

  it('throws ApiError with detail on 400', async () => {
    mockFetch.mockReturnValue(
      Promise.resolve({
        ok: false,
        status: 400,
        text: () => Promise.resolve(JSON.stringify({ detail: 'Insufficient cash' })),
      }),
    );
    await expect(api.trade('AAPL', 999999, 'buy')).rejects.toMatchObject({
      message: 'Insufficient cash',
      status: 400,
    });
    await expect(api.trade('AAPL', 999999, 'buy')).rejects.toBeInstanceOf(
      ApiError,
    );
  });
});
