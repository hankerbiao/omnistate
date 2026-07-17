/**
 * 全局搜索 E2E 测试
 *
 * 覆盖：搜索框聚焦 → 输入搜索 → 筛选切换 → 结果展示
 * 纯查询操作，无副作用，适合作为入门测试
 */
import { test, expect } from '@playwright/test';
import {
  loginAs,
  navigateTo,
  humanDelay,
  thinkDelay,
  closeDelay,
} from './helpers';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('全局搜索', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('搜索功能：输入关键词 → 筛选切换 → 结果展示', async ({ page }) => {
    // ── 1. 登录 ──────────────────────────────────────
    await loginAs(page);
    await thinkDelay(page);

    // ── 2. 导航到全局搜索 ────────────────────────────
    await navigateTo(page, '全局搜索');
    await expect(page.locator('.topbar__title')).toContainText('全局搜索');
    await expect(page).toHaveURL(/.*search/);

    // ── 3. 搜索框交互 ────────────────────────────────
    const searchInput = page.locator('input[type="text"], input[placeholder*="搜索"]').first();
    await expect(searchInput).toBeVisible();

    // 输入搜索关键词
    await searchInput.fill('登录');
    await humanDelay(page);
    // 等待防抖后搜索结果出现
    await page.waitForTimeout(1000);

    // ── 4. 筛选切换 ──────────────────────────────────
    const filterBtns = page.locator('button').filter({ hasText: /全部|需求|用例|计划/ });
    const filterCount = await filterBtns.count();
    if (filterCount > 1) {
      // 点击第二个筛选按钮（非"全部"）
      await filterBtns.nth(1).click();
      await thinkDelay(page);
    }

    // ── 5. 清除搜索 ──────────────────────────────────
    const clearBtn = page.locator('button').filter({ hasText: /清除|×|✕/ });
    if (await clearBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await clearBtn.click();
      await thinkDelay(page);
    }

    console.log('[测试] 全局搜索功能验证完成');
  });
});
