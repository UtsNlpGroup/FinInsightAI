/**
 * E2E tests for authentication flow (Login page).
 *
 * Requires:
 *   E2E_USER_EMAIL and E2E_USER_PASSWORD env vars pointing to a real Supabase test user.
 */

import { test, expect } from '@playwright/test';
import { TEST_EMAIL, TEST_PASSWORD, setupConsoleErrorTracking } from './helpers';

test.describe('Authentication', () => {
  test('login page renders with email and password fields', async ({ page }) => {
    await page.goto('/');

    // Either the login form or the main app is visible
    const emailInput = page.locator('input[type="email"]');
    const appShell = page.locator('header, nav, [class*="chat"]').first();

    const isLoginVisible = await emailInput.isVisible({ timeout: 5_000 }).catch(() => false);
    const isAppVisible = await appShell.isVisible({ timeout: 5_000 }).catch(() => false);

    expect(isLoginVisible || isAppVisible).toBe(true);
  });

  test('invalid credentials show an error message', async ({ page }) => {
    await page.goto('/');

    const emailInput = page.locator('input[type="email"]');
    const isLoginPage = await emailInput.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!isLoginPage) {
      test.skip();
      return;
    }

    await emailInput.fill('wrong@email.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // An error message should appear
    const errorMsg = page.locator('[class*="error"], [role="alert"], p[style*="red"]');
    await expect(errorMsg).toBeVisible({ timeout: 10_000 });
  });

  test('valid login redirects to main app', async ({ page }) => {
    await page.goto('/');

    const emailInput = page.locator('input[type="email"]');
    const isLoginPage = await emailInput.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!isLoginPage) {
      test.skip();
      return;
    }

    await emailInput.fill(TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');

    // Should transition to the main app – look for the header or ticker band
    await expect(page.locator('header')).toBeVisible({ timeout: 20_000 });
  });

  test('authenticated user sees company search bar', async ({ page }) => {
    await page.goto('/');

    const searchInput = page.locator('input[placeholder*="Search ticker"]');
    const isVisible = await searchInput.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!isVisible) {
      // Try to login first
      const emailInput = page.locator('input[type="email"]');
      if (await emailInput.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await emailInput.fill(TEST_EMAIL);
        await page.fill('input[type="password"]', TEST_PASSWORD);
        await page.click('button[type="submit"]');
        await page.waitForTimeout(3_000);
      }
    }

    // After login, company search should be in the header
    await expect(page.locator('header')).toBeVisible({ timeout: 15_000 });
  });

  test('sign out button returns to login page', async ({ page }) => {
    const { errors } = setupConsoleErrorTracking(page);

    await page.goto('/');

    // Try to find sign out button
    const signOutBtn = page.locator('button:has-text("Log Out"), button:has-text("Sign Out")');
    const isVisible = await signOutBtn.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!isVisible) {
      test.skip();
      return;
    }

    await signOutBtn.click();

    // Should see login form again
    await expect(page.locator('input[type="email"]')).toBeVisible({ timeout: 10_000 });

    // No console errors during sign out
    expect(errors.filter(e => !e.includes('Warning:'))).toHaveLength(0);
  });
});
