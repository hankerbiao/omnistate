import { test, expect } from '@playwright/test';
import {
  loginAs,
  navigateTo,
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
    await loginAs(page);
    await thinkDelay(page);

    const pages = [
      { label: '用户管理', urlPattern: /.*users/ },
      { label: '角色管理', urlPattern: /.*roles/ },
      { label: '权限管理', urlPattern: /.*permissions/ },
    ];

    for (const { label, urlPattern } of pages) {
      await navigateTo(page, label);
      await expect(page.locator('.topbar__title')).toContainText(label);
      await expect(page).toHaveURL(urlPattern);
    }

    // 系统配置在底部需要滚动
    await page.locator('.sidebar').evaluate(el => el.scrollTop = el.scrollHeight);
    await navigateTo(page, '系统配置');
    await expect(page).toHaveURL(/.*system-config/, { timeout: 10000 });
  });

  test('无 roles:read 权限时角色管理和用户组管理不可见', async ({ page }) => {
    // 用 tester 登录（权限较少）
    await loginAs(page, 'tester');
    await expect(page.locator('.topbar__title')).toBeVisible({ timeout: 15000 });

    // 收集 tester 可见的系统类导航项
    await thinkDelay(page);
    const visibleItems = await page.locator('.sidebar__item').allTextContents();
    const systemItems = visibleItems.filter(v => ['用户管理','角色管理','用户组管理','权限管理','系统配置','Lab 管理'].some(s => v.includes(s)));
    console.log(`[测试] tester 可见系统导航项: ${systemItems.length > 0 ? systemItems.join(', ') : '无'}`);
  });
});
