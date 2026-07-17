/**
 * Lab 目录创建 E2E 测试
 *
 * 覆盖：AI 数据生成 → 导航到 Lab 管理 → 打开新建弹窗
 *       → 填写字段（含 Code 自动建议交互） → 提交 → 验证成功
 */
import { test, expect } from '@playwright/test';
import { loginAs, navigateTo, humanDelay, thinkDelay, closeDelay } from './helpers';
import { generateLabData } from './ai-helper';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('创建 Lab', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('AI 生成数据 → 打开新建弹窗 → 填写字段（含 Code 建议） → 提交创建 → 验证成功', async ({ page }) => {
    // ── 1. AI 生成测试数据 ──────────────────────────────
    const aiData = await generateLabData('E2E 自动化测试使用的验证 Lab 目录');
    // ai-helper 内部已追加时间戳
    console.log(`[AI] 生成 Lab 名称: ${aiData.name} (Code: ${aiData.code})`);

    // ── 2. 登录 + 导航到 Lab 管理页面 ──────────────────
    await loginAs(page);
    await navigateTo(page, 'Lab 管理');
    await expect(page.locator('.topbar__title')).toContainText('Lab 管理');
    await expect(page).toHaveURL(/.*catalog-labs/);

    // ── 3. 点击"+ 新建 Lab"按钮 ────────────────────────
    await thinkDelay(page);
    await page.getByRole('button', { name: '+ 新建 Lab' }).click();
    await thinkDelay(page);

    await expect(page.getByText('新建 Lab')).toBeVisible();

    // ── 4. 填写显示名称（触发 Code 自动建议） ──────────
    const nameInput = page.locator('div').filter({ has: page.locator('label', { hasText: '显示名称' }) }).locator('input');
    await nameInput.fill(aiData.name);
    await humanDelay(page);

    // ── 5. 使用建议 Code 按钮（AI 生成的 Code 替代建议值） ──
    // 点击"使用建议 Code"按钮填入自动生成的 Code
    const useSuggestionBtn = page.getByRole('button', { name: /使用建议 Code/ });
    if (await useSuggestionBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await useSuggestionBtn.click();
      await humanDelay(page);
    } else {
      // 手动填写 AI 生成的 Code
      const codeInput = page.locator('div').filter({ has: page.locator('label', { hasText: 'Code' }) }).locator('input');
      await codeInput.fill(aiData.code.toUpperCase());
      await humanDelay(page);
    }

    // 描述（可选）
    const descTextarea = page.locator('div').filter({ has: page.locator('label', { hasText: '描述' }) }).locator('textarea');
    await descTextarea.fill(aiData.description);
    await humanDelay(page);

    // 排序权重
    const sortInput = page.locator('div').filter({ has: page.locator('label', { hasText: '排序权重' }) }).locator('input');
    await sortInput.fill('10');
    await humanDelay(page);

    // ── 6. 提交创建 ──────────────────────────────────────
    await page.getByRole('button', { name: '创建 Lab' }).click();
    await thinkDelay(page);

    // ── 7. 验证弹窗关闭 + Lab 出现在列表中 ──────────────
    await expect(page.getByText('新建 Lab')).not.toBeVisible({ timeout: 10000 });
    // 验证新 Lab 在表格中可见（按名称匹配）
    await expect(page.getByText(aiData.name).first()).toBeVisible({ timeout: 10000 });
    console.log(`[验证] Lab"${aiData.name}"已出现在列表中`);
  });
});
