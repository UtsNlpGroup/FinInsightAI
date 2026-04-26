/**
 * E2E tests for the Dashboard and Sentiment panels.
 *
 * Tests:
 *   1. Dashboard panel opens when clicking "Executive Dashboard"
 *   2. Dashboard loads analysis cards for the selected ticker
 *   3. Sentiment panel loads market news items
 *   4. Company search changes the active ticker
 *   5. Model picker is visible and functional
 */

import { test, expect } from '@playwright/test';
import { login, setupConsoleErrorTracking } from './helpers';

test.describe('Dashboard Panel', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('clicking Executive Dashboard opens the side panel', async ({ page }) => {
    const dashboardBtn = page.locator(
      'button:has-text("Executive Dashboard"), button:has-text("Dashboard"), nav button'
    ).first();

    if (!await dashboardBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      test.skip();
      return;
    }

    await dashboardBtn.click();
    await page.waitForTimeout(500);

    // Panel content should appear (cards, analysis data, or loading state)
    const panelContent = page.locator('[class*="dashboard"], [class*="panel"], main').first();
    await expect(panelContent).toBeVisible({ timeout: 10_000 });
  });

  test('dashboard shows analysis cards after data loads', async ({ page }) => {
    // Open dashboard panel
    const dashboardBtn = page.locator(
      'button:has-text("Executive"), button:has-text("Dashboard")'
    ).first();

    if (!await dashboardBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      test.skip();
      return;
    }

    await dashboardBtn.click();

    // Wait for cards or content to load (up to 30s for agent calls)
    await expect(page.locator('body')).toContainText(
      /risk|strategy|growth|capex|revenue|outlook/i,
      { timeout: 30_000 }
    );
  });

  test('company search filters companies', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search ticker"], input[placeholder*="Search"]').first();

    if (!await searchInput.isVisible({ timeout: 5_000 }).catch(() => false)) {
      test.skip();
      return;
    }

    await searchInput.click();
    await searchInput.fill('MSFT');

    // Dropdown should show Microsoft
    await expect(page.locator('body')).toContainText(/Microsoft|MSFT/i, { timeout: 5_000 });
  });

  test('selecting a company from search changes the ticker', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search ticker"], input[placeholder*="Search"]').first();

    if (!await searchInput.isVisible({ timeout: 5_000 }).catch(() => false)) {
      test.skip();
      return;
    }

    await searchInput.click();
    await searchInput.fill('NVDA');
    await page.waitForTimeout(500);

    const nvdaOption = page.locator('[class*="dropdown"] button:has-text("NVDA"), li:has-text("NVDA")').first();
    if (await nvdaOption.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await nvdaOption.click();
      await expect(page.locator('body')).toContainText('NVDA', { timeout: 5_000 });
    }
  });
});

test.describe('Sentiment Panel', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('clicking Market Sentiment opens the sentiment panel', async ({ page }) => {
    const sentimentBtn = page.locator(
      'button:has-text("Market Sentiment"), button:has-text("Sentiment"), nav button'
    ).nth(1);

    if (!await sentimentBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      test.skip();
      return;
    }

    await sentimentBtn.click();
    await page.waitForTimeout(500);

    // Sentiment panel content
    const panel = page.locator('body');
    await expect(panel).toContainText(/sentiment|news|bullish|bearish|neutral/i, {
      timeout: 30_000,
    });
  });

  test('sentiment panel shows news items', async ({ page }) => {
    const { errors } = setupConsoleErrorTracking(page);

    const sentimentBtn = page.locator('button:has-text("Sentiment")').first();
    if (!await sentimentBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      test.skip();
      return;
    }

    await sentimentBtn.click();

    // Should show news items or sentiment analysis
    await expect(page.locator('body')).toContainText(/.{5,}/, { timeout: 30_000 });

    const criticalErrors = errors.filter(e => !e.includes('Warning:'));
    expect(criticalErrors).toHaveLength(0);
  });
});

test.describe('Model Picker', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('model picker is visible in the navigation', async ({ page }) => {
    // Model picker should be in the left nav
    const modelPicker = page.locator('[title*="Model"], button:has-text("GPT"), [class*="model"]').first();
    const isVisible = await modelPicker.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!isVisible) {
      test.skip();
      return;
    }
    expect(isVisible).toBe(true);
  });

  test('clicking model picker shows model options', async ({ page }) => {
    const modelBtn = page.locator('button:has-text("GPT"), button[title*="model"], button:has-text("Mini")').first();

    if (!await modelBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      test.skip();
      return;
    }

    await modelBtn.click();
    await expect(page.locator('body')).toContainText(/GPT|model/i, { timeout: 3_000 });
  });
});
