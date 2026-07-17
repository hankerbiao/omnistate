/**
 * 页面冒烟测试
 *
 * 将 6 个弱测试（仅验证页面可访问无实质断言）合并为单个烟雾测试，
 * 在一个 describe 中以循环方式验证所有页面的可访问性。
 *
 * 覆盖：用例看板、用例治理、预制用例集、项目、Lab 管理
 */
import { test, expect } from '@playwright/test';
import { loginAs, navigateTo, closeDelay } from './helpers';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('页面冒烟测试（Smoke Test）', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('登录 → 依次访问各页面 → 验证标题和 URL', async ({ page }) => {
    await loginAs(page);

    const pages: { label: string; urlPattern: RegExp }[] = [
      { label: '用例看板',   urlPattern: /.*test-cases/ },
      { label: '用例治理',   urlPattern: /.*case-governance/ },
      { label: '预制用例集', urlPattern: /.*collections/ },
      { label: '项目',       urlPattern: /.*projects/ },
      { label: 'Lab 管理',   urlPattern: /.*catalog-labs/ },
    ];

    for (const { label, urlPattern } of pages) {
      await navigateTo(page, label);
      await expect(page.locator('.topbar__title')).toContainText(label);
      await expect(page).toHaveURL(urlPattern);
      // 验证侧边栏高亮同步
      await expect(page.locator('.sidebar__item--active').filter({ hasText: label })).toBeVisible();
      console.log(`[冒烟] ${label} ✓`);
    }
  });
});
