import { test, expect } from '@playwright/test';
import { waitForAppReady, readHeaderCash } from './helpers';

const DEFAULT_TICKERS = [
  'AAPL',
  'GOOGL',
  'MSFT',
  'AMZN',
  'TSLA',
  'NVDA',
  'META',
  'JPM',
  'V',
  'NFLX',
];

test.describe('PLAN §12: Fresh start', () => {
  test('app loads with default watchlist, $10,000 cash, and streaming prices', async ({
    page,
  }) => {
    await page.goto('/');
    await waitForAppReady(page);

    // 10 default tickers visible in the watchlist.
    for (const ticker of DEFAULT_TICKERS) {
      await expect(
        page.getByTestId(`watchlist-row-${ticker}`),
        `watchlist should contain ${ticker}`,
      ).toBeVisible();
    }
    await expect(page.locator('[data-testid^="watchlist-row-"]')).toHaveCount(
      DEFAULT_TICKERS.length,
    );

    // Fresh portfolio: $10,000 cash.
    expect(await readHeaderCash(page)).toBe(10000);

    // Prices are streaming: a watchlist price cell text changes within a few
    // seconds, driven by the SSE stream. AAPL is the first row.
    const priceCell = page
      .getByTestId('watchlist-row-AAPL')
      .locator('td')
      .nth(1);
    const initial = (await priceCell.innerText()).trim();
    await expect
      .poll(async () => (await priceCell.innerText()).trim(), {
        timeout: 20_000,
        message: 'AAPL price should update from the SSE stream',
      })
      .not.toBe(initial);
  });

  test('connection status indicator shows connected', async ({ page }) => {
    await page.goto('/');
    await waitForAppReady(page);

    const dot = page.getByTestId('connection-status');
    await expect
      .poll(async () => dot.getAttribute('data-status'), { timeout: 20_000 })
      .toBe('connected');
    await expect(dot).toContainText('Connected');
  });

  test('an EventSource request to /api/stream/prices is established', async ({
    page,
  }) => {
    const sseRequest = page.waitForRequest(
      (req) => req.url().includes('/api/stream/prices'),
      { timeout: 20_000 },
    );
    await page.goto('/');
    const req = await sseRequest;
    expect(req.url()).toContain('/api/stream/prices');
  });
});
