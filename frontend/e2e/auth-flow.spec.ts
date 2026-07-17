import { test, expect } from '@playwright/test';
import { closeDelay } from './helpers';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('保护路由', () => {
  test('无 token 时直接访问受保护路由应跳转到登录页', async ({ page }) => {
    await page.goto('/my-tasks');
    await expect(page.locator('#user_id')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('h1')).toContainText('DML Sentio');
  });
});
