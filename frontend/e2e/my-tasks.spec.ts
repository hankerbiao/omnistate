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

test.describe('我的任务页面', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('完整流程：导航到我的任务 → 验证页面 → 直接访问', async ({ page }) => {
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill(DEFAULT_USER_ID);
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page).toBeDefined();
    await thinkDelay(page);

    await page.locator('.sidebar__item').filter({ hasText: '我的任务' }).click();
    await thinkDelay(page);
    await expect(page.locator('.topbar__title')).toContainText('我的任务');
    await expect(page).toHaveURL(/.*my-tasks/);
    await expect(page.locator('.sidebar__item--active').filter({ hasText: '我的任务' })).toBeVisible();

    await page.goto('/my-tasks');
    await thinkDelay(page);
    await expect(page.locator('.topbar__title')).toContainText('我的任务', { timeout: 10000 });
  });

  test('无 dashboard 权限时默认跳转到 my-tasks', async ({ page }) => {
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill('tester');
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();

    // tester 没有 dashboard 权限，默认跳转 my-tasks
    await expect(page).toHaveURL(/.*my-tasks/, { timeout: 15000 });
    await expect(page.locator('.topbar__title')).toContainText('我的任务');
  });
});
