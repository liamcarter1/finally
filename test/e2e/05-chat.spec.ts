import { test, expect } from '@playwright/test';
import { waitForAppReady, readHeaderCash } from './helpers';

test.describe('PLAN §12: AI chat (mocked LLM)', () => {
  test('buy via chat shows a response, inline trade confirmation, and updates portfolio', async ({
    page,
  }) => {
    await page.goto('/');
    await waitForAppReady(page);

    // Chat panel renders expanded by default; ensure the input is present.
    const input = page.getByLabel('Message');
    await expect(input).toBeVisible();

    const cashBefore = await readHeaderCash(page);

    await input.fill('buy 1 AAPL');
    await page.getByRole('button', { name: 'Send' }).click();

    // Assistant text response appears.
    await expect(
      page.getByTestId('chat-message-assistant').last(),
    ).toContainText('AAPL', { timeout: 15_000 });

    // Inline trade confirmation (executed).
    const confirmation = page.getByTestId('chat-trade-confirmation').last();
    await expect(confirmation).toBeVisible({ timeout: 15_000 });
    await expect(confirmation).toContainText('AAPL');
    await expect(confirmation).toContainText('BUY');

    // Position + cash reflect the trade.
    await expect(
      page.getByTestId('position-row-AAPL'),
    ).toBeVisible({ timeout: 15_000 });
    await expect
      .poll(async () => readHeaderCash(page), { timeout: 15_000 })
      .toBeLessThan(cashBefore);
  });

  test('analytical message returns a text response with no action', async ({
    page,
  }) => {
    await page.goto('/');
    await waitForAppReady(page);

    const input = page.getByLabel('Message');
    await input.fill('how is my portfolio doing?');
    await page.getByRole('button', { name: 'Send' }).click();

    const reply = page.getByTestId('chat-message-assistant').last();
    await expect(reply).toBeVisible({ timeout: 15_000 });
    await expect(reply).toContainText('portfolio', { timeout: 15_000 });
    // No trade confirmation attached to this analytical reply.
    await expect(
      reply.getByTestId('chat-trade-confirmation'),
    ).toHaveCount(0);
  });

  test('add to watchlist via chat applies the change on the backend', async ({
    page,
  }) => {
    await page.goto('/');
    await waitForAppReady(page);

    const NEW = 'PYPL';
    // Clean slate.
    const existing = page.getByTestId(`watchlist-row-${NEW}`);
    if (await existing.count()) {
      await page.getByRole('button', { name: `Remove ${NEW}` }).click();
      await expect(existing).toHaveCount(0);
    }

    const input = page.getByLabel('Message');
    await input.fill(`add ${NEW} to watchlist`);
    await page.getByRole('button', { name: 'Send' }).click();

    await expect(
      page.getByTestId('chat-message-assistant').last(),
    ).toContainText(NEW, { timeout: 15_000 });

    // The backend applies the add and the page refreshes the watchlist:
    // the new ticker row should appear.
    await expect(
      page.getByTestId(`watchlist-row-${NEW}`),
    ).toBeVisible({ timeout: 15_000 });

    // Cleanup.
    await page.getByRole('button', { name: `Remove ${NEW}` }).click();
  });
});
