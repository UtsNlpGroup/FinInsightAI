import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration for FinsightAI frontend.
 *
 * Prerequisites:
 *   - Full stack running via `docker compose up` (backend :8001, frontend :5173)
 *   - A test user with credentials in environment:
 *       E2E_USER_EMAIL=test@example.com
 *       E2E_USER_PASSWORD=testpassword123
 *
 * Run all E2E tests:
 *   npx playwright test
 *
 * Run with UI:
 *   npx playwright test --ui
 *
 * Run specific spec:
 *   npx playwright test e2e/chat.spec.ts
 */

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,   // financial agent responses are slow – run serially
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 120_000,       // 2 minutes per test (agent can be slow)

  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'playwright-results.json' }],
    ['list'],
  ],

  use: {
    baseURL: process.env.FRONTEND_URL ?? 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    actionTimeout: 30_000,
    navigationTimeout: 30_000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 7'] },
      testMatch: 'e2e/mobile*.spec.ts',
    },
  ],

  // Start the dev server automatically in local development
  webServer: process.env.CI
    ? undefined
    : {
        command: 'npm run dev',
        url: 'http://localhost:5173',
        reuseExistingServer: true,
        timeout: 60_000,
      },
});
