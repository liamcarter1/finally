import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for the FinAlly E2E suite.
 *
 * The suite is self-contained: `webServer` boots the FastAPI backend (which
 * also serves the built frontend at `/`) in deterministic E2E mode
 * (LLM_MOCK=true, simulator market data, throwaway SQLite) via
 * `scripts/start-backend.mjs`. baseURL targets that server.
 *
 * To run against an already-running server (e.g. the Docker container on
 * :8000), set E2E_NO_SERVER=1 to skip the managed webServer.
 */
const PORT = process.env.E2E_PORT || '8000';
const HOST = process.env.E2E_HOST || '127.0.0.1';
const baseURL = process.env.E2E_BASE_URL || `http://${HOST}:${PORT}`;

export default defineConfig({
  testDir: './e2e',
  // The simulator and 30s snapshot task make some flows inherently timing
  // dependent; run serially with a single worker for deterministic state.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: process.env.E2E_NO_SERVER
    ? undefined
    : {
        command: 'node scripts/start-backend.mjs',
        url: `${baseURL}/api/health`,
        // Always boot a fresh backend (fresh throwaway DB) so the suite starts
        // from the seeded $10,000 / 10-ticker state. Reusing a server left
        // dirty by a prior run would break the fresh-start assertions.
        reuseExistingServer: false,
        timeout: 120_000,
        stdout: 'ignore',
        stderr: 'pipe',
      },
});
