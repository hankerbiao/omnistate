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

test.describe('系统管理页面', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('管理员可导航到全部管理页面：用户管理 → 角色管理 → 权限管理 → 系统配置', async ({ page }) => {
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill(DEFAULT_USER_ID);
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page).toBeDefined();
    await thinkDelay(page);

    const pages = [
      { label: '用户管理', urlPattern: /.*users/ },
      { label: '角色管理', urlPattern: /.*roles/ },
      { label: '权限管理', urlPattern: /.*permissions/ },
    ];

    for (const { label, urlPattern } of pages) {
      await page.locator('.sidebar__item').filter({ hasText: label }).click();
      await thinkDelay(page);
      await expect(page.locator('.topbar__title')).toContainText(label);
      await expect(page).toHaveURL(urlPattern);
    }

    // 系统配置在底部需要滚动
    await page.locator('.sidebar').evaluate(el => el.scrollTop = el.scrollHeight);
    await thinkDelay(page);
    await page.locator('.sidebar__item').filter({ hasText: '系统配置' }).click();
    await thinkDelay(page);
    await expect(page).toHaveURL(/.*system-config/, { timeout: 10000 });
  });

  test('无 roles:read 权限时角色管理和用户组管理不可见', async ({ page }) => {
    // 用 tester 登录（权限较少）
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill('tester');
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page.locator('.topbar__title')).toBeVisible({ timeout: 15000 });
    await thinkDelay(page);

    // tester 看不到角色管理
    await expect(page.locator('.sidebar__item').filter({ hasText: '角色管理' })).not.toBeVisible();
  });
});
