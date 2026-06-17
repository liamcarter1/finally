import { test, expect } from '@playwright/test';
import { waitForAppReady, readHeaderCash } from './helpers';

test.describe('PLAN §12: Buy and sell shares', () => {
  test('buy shares: cash decreases, position appears, total updates', async ({
    page,
  }) => {
    await page.goto('/');
    await waitForAppReady(page);

    const TICKER = 'MSFT';
    const QTY = 2;
    const cashBefore = await readHeaderCash(page);

    // Trade bar: ticker + qty + Buy.
    await page.getByLabel('Ticker', { exact: true }).fill(TICKER);
    await page.getByLabel('Quantity').fill(String(QTY));
    await page.getByRole('button', { name: 'Buy', exact: true }).click();

    // Inline confirmation status.
    await expect(page.getByRole('status')).toContainText('BUY', {
      timeout: 15_000,
    });

    // A position row appears.
    await expect(
      page.getByTestId(`position-row-${TICKER}`),
    ).toBeVisible({ timeout: 15_000 });

    // Cash decreased.
    await expect
      .poll(async () => readHeaderCash(page), { timeout: 15_000 })
      .toBeLessThan(cashBefore);

    // Total value remains a real, positive number near the starting capital.
    await expect
      .poll(
        async () =>
          Number(
            (await page.getByTestId('header-total-value').innerText()).replace(
              /[^0-9.\-]/g,
              '',
            ),
          ),
        { timeout: 15_000 },
      )
      .toBeGreaterThan(0);
  });

  test('sell shares: cash increases, position updates or disappears', async ({
    page,
  }) => {
    await page.goto('/');
    await waitForAppReady(page);

    const TICKER = 'JPM';

    // Establish a known position first (buy 3).
    await page.getByLabel('Ticker', { exact: true }).fill(TICKER);
    await page.getByLabel('Quantity').fill('3');
    await page.getByRole('button', { name: 'Buy', exact: true }).click();
    await expect(
      page.getByTestId(`position-row-${TICKER}`),
    ).toBeVisible({ timeout: 15_000 });

    const cashAfterBuy = await readHeaderCash(page);

    // Sell the entire position (3 shares) -> row should disappear.
    await page.getByLabel('Ticker', { exact: true }).fill(TICKER);
    await page.getByLabel('Quantity').fill('3');
    await page.getByRole('button', { name: 'Sell', exact: true }).click();
    await expect(page.getByRole('status')).toContainText('SELL', {
      timeout: 15_000,
    });

    // Cash increased relative to the post-buy balance.
    await expect
      .poll(async () => readHeaderCash(page), { timeout: 15_000 })
      .toBeGreaterThan(cashAfterBuy);

    // Position fully sold -> row removed.
    await expect(
      page.getByTestId(`position-row-${TICKER}`),
    ).toHaveCount(0, { timeout: 15_000 });
  });

  test('partial sell: position remains with reduced quantity', async ({
    page,
  }) => {
    await page.goto('/');
    await waitForAppReady(page);

    const TICKER = 'V';

    await page.getByLabel('Ticker', { exact: true }).fill(TICKER);
    await page.getByLabel('Quantity').fill('4');
    await page.getByRole('button', { name: 'Buy', exact: true }).click();
    const posRow = page.getByTestId(`position-row-${TICKER}`);
    await expect(posRow).toBeVisible({ timeout: 15_000 });

    // Sell half.
    await page.getByLabel('Ticker', { exact: true }).fill(TICKER);
    await page.getByLabel('Quantity').fill('2');
    await page.getByRole('button', { name: 'Sell', exact: true }).click();
    await expect(page.getByRole('status')).toContainText('SELL', {
      timeout: 15_000,
    });

    // Position still present (partial sell leaves shares).
    await expect(posRow).toBeVisible({ timeout: 15_000 });
    // Quantity column (2nd cell) reflects the remaining 2 shares.
    await expect
      .poll(async () => (await posRow.locator('td').nth(1).innerText()).trim(), {
        timeout: 15_000,
      })
      .toContain('2');
  });
});
