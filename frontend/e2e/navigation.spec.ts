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

test.describe('侧边栏导航', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('管理员完整导航流程：品牌信息 → 分区可见 → 页面切换 → 高亮切换', async ({ page }) => {
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill(DEFAULT_USER_ID);
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page.locator('.topbar__title')).toBeVisible({ timeout: 15000 });
    await thinkDelay(page);

    await expect(page.locator('.sidebar__brand')).toBeVisible();
    await expect(page.locator('.sidebar__title')).toContainText('TestHub');
    await expect(page.locator('.sidebar__version')).toContainText('测试运营平台');

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
      await page.locator('.sidebar__item').filter({ hasText: label }).click();
      await thinkDelay(page);
      await expect(page.locator('.topbar__title')).toContainText(label);
      await expect(page).toHaveURL(urlPattern);
      await expect(page.locator('.sidebar__item--active').filter({ hasText: label })).toBeVisible();
    }
  });

  test('受限角色（tester）只能看到有权限的导航项', async ({ page }) => {
    // 使用 tester 账号登录（仅有 test_cases:read, execution_plans:read, execution_tasks:read）
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill('tester');
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page.locator('.topbar__title')).toBeVisible({ timeout: 15000 });
    await thinkDelay(page);

    await expect(page.locator('.sidebar__item').filter({ hasText: '用例看板' })).toBeVisible();
    await expect(page.locator('.sidebar__item').filter({ hasText: '执行计划' })).toBeVisible();

    await expect(page.locator('.sidebar__item').filter({ hasText: '系统配置' })).not.toBeVisible();
    await expect(page.locator('.sidebar__item').filter({ hasText: '数据统计' })).not.toBeVisible();
    await expect(page.locator('.sidebar__item').filter({ hasText: '用户管理' })).not.toBeVisible();
  });
});
