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

test.describe('数据统计页面', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('管理员可访问仪表盘：标题/描述/侧边栏高亮', async ({ page }) => {
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill(DEFAULT_USER_ID);
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page).toHaveURL(/.*dashboard/, { timeout: 15000 });
    await thinkDelay(page);

    await expect(page.locator('.topbar__title')).toContainText('数据统计');
    await expect(page.locator('.topbar__desc')).toContainText('测试数据整体概览');
    await expect(page.locator('.sidebar__item--active').filter({ hasText: '数据统计' })).toBeVisible();
  });

  test('无 dashboard 权限时导航项不可见', async ({ page }) => {
    // tester 账号没有 dashboard 权限
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill('tester');
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page.locator('.topbar__title')).toBeVisible({ timeout: 15000 });
    await thinkDelay(page);

    await expect(page.locator('.sidebar__item').filter({ hasText: '数据统计' })).not.toBeVisible();
  });
});
