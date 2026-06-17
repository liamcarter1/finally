import { test, expect } from '@playwright/test';
import { waitForAppReady } from './helpers';

test.describe('PLAN §12: Watchlist add / remove', () => {
  test('add a ticker via the UI, then remove it', async ({ page }) => {
    await page.goto('/');
    await waitForAppReady(page);

    const NEW = 'PYPL';
    const row = page.getByTestId(`watchlist-row-${NEW}`);

    // Ensure a clean starting state (in case a prior run left it).
    if (await row.count()) {
      await page.getByRole('button', { name: `Remove ${NEW}` }).click();
      await expect(row).toHaveCount(0);
    }

    // Add via the watchlist input + Add button.
    await page.getByLabel('Add ticker').fill(NEW);
    await page
      .getByRole('button', { name: 'Add', exact: true })
      .click();

    await expect(row).toBeVisible({ timeout: 15_000 });

    // Remove it again via the row's × button.
    await page.getByRole('button', { name: `Remove ${NEW}` }).click();
    await expect(row).toHaveCount(0, { timeout: 15_000 });
  });
});
