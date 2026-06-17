import { Page, expect } from '@playwright/test';

/** Parse a currency string like "$9,810.13" into a number. Returns NaN if blank/placeholder. */
export function parseCurrency(text: string | null | undefined): number {
  if (!text) return NaN;
  const cleaned = text.replace(/[^0-9.\-]/g, '');
  if (cleaned === '' || cleaned === '-' || cleaned === '.') return NaN;
  return Number(cleaned);
}

/** Read a header stat (Total Value / Cash / Unrealized P&L) as a number. */
export async function readHeaderCash(page: Page): Promise<number> {
  const text = await page.getByTestId('header-cash').innerText();
  return parseCurrency(text);
}

export async function readHeaderTotal(page: Page): Promise<number> {
  const text = await page.getByTestId('header-total-value').innerText();
  return parseCurrency(text);
}

/**
 * Wait until the app has loaded its portfolio (header cash shows a real number,
 * not the "—" placeholder) and the watchlist has rendered rows.
 */
export async function waitForAppReady(page: Page): Promise<void> {
  await expect
    .poll(async () => readHeaderCash(page), { timeout: 20_000 })
    .toBeGreaterThan(0);
  await expect
    .poll(
      async () => page.locator('[data-testid^="watchlist-row-"]').count(),
      { timeout: 20_000 },
    )
    .toBeGreaterThan(0);
}
