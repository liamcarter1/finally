import { test, expect } from '@playwright/test';
import { waitForAppReady } from './helpers';

test.describe('PLAN §12: Portfolio visualization', () => {
  test('heatmap renders a rectangle for a position and P&L chart gets data points', async ({
    page,
  }) => {
    await page.goto('/');
    await waitForAppReady(page);

    const TICKER = 'NVDA';

    // Buy to create a position (and a portfolio snapshot).
    await page.getByLabel('Ticker', { exact: true }).fill(TICKER);
    await page.getByLabel('Quantity').fill('1');
    await page.getByRole('button', { name: 'Buy', exact: true }).click();
    await expect(
      page.getByTestId(`position-row-${TICKER}`),
    ).toBeVisible({ timeout: 15_000 });

    // Heatmap: a recharts Treemap cell is an SVG <rect>. With a position the
    // "No positions yet." placeholder is replaced by the treemap.
    const heatmap = page.getByTestId('heatmap');
    await expect(heatmap).not.toContainText('No positions yet', {
      timeout: 15_000,
    });
    await expect
      .poll(async () => heatmap.locator('rect').count(), { timeout: 15_000 })
      .toBeGreaterThan(0);
    // The position ticker label should appear in the heatmap.
    await expect(heatmap).toContainText(TICKER, { timeout: 15_000 });

    // P&L chart: needs >= 2 snapshots to render a line. A second trade
    // guarantees a second snapshot beyond the seed one.
    await page.getByLabel('Ticker', { exact: true }).fill(TICKER);
    await page.getByLabel('Quantity').fill('1');
    await page.getByRole('button', { name: 'Buy', exact: true }).click();

    const pnl = page.getByTestId('pnl-chart');
    await expect
      .poll(async () => pnl.locator('svg .recharts-line path, svg path').count(), {
        timeout: 25_000,
      })
      .toBeGreaterThan(0);
    await expect(pnl).not.toContainText('Collecting snapshots', {
      timeout: 25_000,
    });
  });
});
