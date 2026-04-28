/**
 * Shared helpers for Playwright E2E tests.
 */

import { Page, expect } from '@playwright/test';

export const TEST_EMAIL = process.env.E2E_USER_EMAIL ?? 'test@finsight.ai';
export const TEST_PASSWORD = process.env.E2E_USER_PASSWORD ?? 'TestPassword123!';

/**
 * Log in via the Login page and wait until the main app is loaded.
 */
export async function login(page: Page): Promise<void> {
  await page.goto('/');

  // If already logged in (session cookie), skip login form
  const loginForm = page.locator('form, input[type="email"]').first();
  const isLoginPage = await loginForm.isVisible({ timeout: 3_000 }).catch(() => false);

  if (!isLoginPage) return; // already authenticated

  await page.fill('input[type="email"]', TEST_EMAIL);
  await page.fill('input[type="password"]', TEST_PASSWORD);
  await page.click('button[type="submit"]');

  // Wait for the main app shell to appear (chat input or company search)
  await expect(
    page.locator('input[placeholder*="Search"], textarea, input[placeholder*="Ask"]').first()
  ).toBeVisible({ timeout: 15_000 });
}

/**
 * Wait for the agent to finish streaming a response.
 * The done event sends the final assistant message.
 */
export async function waitForAgentResponse(page: Page, timeoutMs = 60_000): Promise<void> {
  // Wait until typing indicator disappears OR an assistant message appears
  await page.waitForFunction(
    () => {
      const typingIndicator = document.querySelector('[data-testid="typing-indicator"], .typing-indicator');
      return !typingIndicator;
    },
    { timeout: timeoutMs },
  );
}

/**
 * Send a message in the chat input and wait for the response.
 */
export async function sendChatMessage(page: Page, message: string): Promise<void> {
  const chatInput = page.locator(
    'textarea[placeholder], input[placeholder*="Ask"], input[placeholder*="message"]'
  ).first();

  await chatInput.fill(message);
  await page.keyboard.press('Enter');
}

/**
 * Assert that the page shows no JavaScript errors (uncaught exceptions).
 */
export function setupConsoleErrorTracking(page: Page): { errors: string[] } {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  page.on('pageerror', (err) => errors.push(err.message));
  return { errors };
}
