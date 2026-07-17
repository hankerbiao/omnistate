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

test.describe('侧边栏导航', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('管理员完整导航流程：品牌信息 → 分区可见 → 页面切换 → 高亮切换', async ({ page }) => {
    await loginAs(page);
    await expect(page.locator('.topbar__title')).toBeVisible({ timeout: 15000 });
    await thinkDelay(page);

    await expect(page.locator('.sidebar__brand')).toBeVisible();
    await expect(page.locator('.sidebar__title')).toContainText('DML Sentio');
    await expect(page.locator('.sidebar__version')).toContainText('测试管理平台');

    await expect(page.locator('.sidebar__section-label').filter({ hasText: '概览' })).toBeVisible();
    await expect(page.locator('.sidebar__section-label').filter({ hasText: '测试资产' })).toBeVisible();
    await expect(page.locator('.sidebar__section-label').filter({ hasText: '执行' })).toBeVisible();
    await expect(page.locator('.sidebar__section-label').filter({ hasText: '系统' })).toBeVisible();

    for (const { label, urlPattern } of [
      { label: '我的任务', urlPattern: /.*my-tasks/ },
      { label: '用例看板', urlPattern: /.*test-cases/ },
      { label: '执行计划', urlPattern: /.*execution-plans/ },
      { label: '数据统计', urlPattern: /.*dashboard/ },
    ]) {
      await navigateTo(page, label);
      await expect(page.locator('.topbar__title')).toContainText(label);
      await expect(page).toHaveURL(urlPattern);
      await expect(page.locator('.sidebar__item--active').filter({ hasText: label })).toBeVisible();
    }
  });

  test('受限角色（tester）导航项验证', async ({ page }) => {
    // 使用 tester 账号登录，验证权限控制的导航项可见性
    await loginAs(page, 'tester');
    await expect(page.locator('.topbar__title')).toBeVisible({ timeout: 15000 });
    await thinkDelay(page);

    // 收集可见的导航项
    const visibleItems = await page.locator('.sidebar__item').allTextContents();
    console.log(`[测试] tester 可见导航项: ${visibleItems.join(', ')}`);

    // 基础断言：tester 应该能看到"用例看板"（通用权限）
    await expect(page.locator('.sidebar__item').filter({ hasText: '用例看板' })).toBeVisible();
  });
});
