import { test, expect } from '@playwright/test';
import { waitForAppReady } from './helpers';

test.describe('PLAN §12: SSE resilience', () => {
  test('connection indicator reads connected once streaming', async ({
    page,
  }) => {
    await page.goto('/');
    await waitForAppReady(page);

    const dot = page.getByTestId('connection-status');
    await expect
      .poll(async () => dot.getAttribute('data-status'), { timeout: 20_000 })
      .toBe('connected');
  });

  test('indicator reflects a broken stream, then recovers when it returns', async ({
    page,
  }) => {
    const dot = page.getByTestId('connection-status');

    // Break the SSE stream before load: every connection attempt is aborted,
    // so the EventSource errors and the indicator never reaches "connected".
    let breakStream = true;
    await page.route('**/api/stream/prices', async (route) => {
      if (breakStream) {
        await route.abort();
      } else {
        await route.continue();
      }
    });

    await page.goto('/');
    // The portfolio REST calls still succeed, so the app shell loads; but the
    // connection dot should not be "connected" while the stream is down.
    await expect
      .poll(async () => dot.getAttribute('data-status'), { timeout: 20_000 })
      .not.toBe('connected');

    // Restore the stream and reload: EventSource connects and the dot recovers.
    breakStream = false;
    await page.reload();
    await waitForAppReady(page);
    await expect
      .poll(async () => dot.getAttribute('data-status'), { timeout: 25_000 })
      .toBe('connected');
  });
});
