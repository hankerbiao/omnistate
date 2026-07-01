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

test.describe('用户切换', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('完整切换流程：用户列表展示 → 当前高亮禁用 → 切换后权限更新', async ({ page }) => {
    // 以 admin 登录
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill(DEFAULT_USER_ID);
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page.locator('.topbar__title')).toBeVisible({ timeout: 15000 });
    await thinkDelay(page);

    // 用户列表展示
    const userSwitcher = page.locator('[role="group"][aria-label="切换用户"]');
    await expect(userSwitcher).toBeVisible();

    // 管理员 chip 高亮且禁用
    const adminChip = page.locator('.topbar__user-chip--active').filter({ hasText: '管理员' });
    await expect(adminChip).toBeVisible();
    await expect(adminChip).toBeDisabled();

    // 管理员能看到系统配置
    await expect(page.locator('.sidebar__item').filter({ hasText: '系统配置' })).toBeVisible();

    // 切换到 tester
    await humanDelay(page);
    await page.locator('.topbar__user-chip').filter({ hasText: '测试人员' }).click();
    await thinkDelay(page);
    await page.waitForTimeout(1000);

    // 权限更新
    await expect(page.locator('.sidebar__item').filter({ hasText: '系统配置' })).not.toBeVisible();
    await expect(page.locator('.sidebar__item').filter({ hasText: '用例看板' })).toBeVisible();

    const activeChip = page.locator('.topbar__user-chip--active');
    await expect(activeChip).toContainText('测试人员');
  });
});
