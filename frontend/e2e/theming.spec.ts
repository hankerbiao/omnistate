import { test, expect } from '@playwright/test';
import {
  DEFAULT_USER_ID,
  DEFAULT_PASSWORD,
  humanDelay,
  thinkDelay,
  closeDelay,
} from './helpers';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('主题切换', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('完整主题流程：按钮存在 → 切换主题 → 刷新后保持', async ({ page }) => {
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill(DEFAULT_USER_ID);
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page.locator('.topbar__title')).toBeVisible({ timeout: 15000 });
    await thinkDelay(page);

    const themeButton = page.getByRole('button', { name: '切换主题' });
    await expect(themeButton).toBeVisible();

    const initialTheme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme') || localStorage.getItem('theme') || 'light'
    );

    await humanDelay(page);
    await themeButton.click();
    await page.waitForTimeout(500);

    const newTheme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme') || localStorage.getItem('theme')
    );
    expect(newTheme).not.toBe(initialTheme);

    await page.reload();
    await expect(page.locator('.topbar__title')).toBeVisible({ timeout: 15000 });
    const persistedTheme = await page.evaluate(() =>
      document.documentElement.getAttribute('data-theme') || localStorage.getItem('theme')
    );
    expect(persistedTheme).toBe(newTheme);
  });
});
