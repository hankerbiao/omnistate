/**
 * 预制用例集创建 E2E 测试
 *
 * 覆盖：AI 数据生成 → 导航到预制用例集 → 打开新建弹窗
 *       → 填写字段（集合名称/描述/标签） → 提交 → 验证成功
 */
import { test, expect } from '@playwright/test';
import { loginAs, navigateTo, humanDelay, thinkDelay, closeDelay } from './helpers';
import { generateCollectionData } from './ai-helper';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('创建预制用例集', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('AI 生成数据 → 打开新建弹窗 → 填写字段 → 提交创建 → 验证成功', async ({ page }) => {
    // ── 1. AI 生成测试数据 ──────────────────────────────
    const aiData = await generateCollectionData(
      'E2E 自动化回归测试基线集合，包含登录、权限、数据校验等测试用例'
    );
    // ai-helper 内部已追加时间戳
    const tagsStr = aiData.tags.slice(0, 3).join(', ');
    console.log(`[AI] 生成集合名称: ${aiData.name} (标签: ${tagsStr})`);

    // ── 2. 登录 + 导航到预制用例集页面 ─────────────────
    await loginAs(page);
    await navigateTo(page, '预制用例集');
    await expect(page.locator('.topbar__title')).toContainText('预制用例集');
    await expect(page).toHaveURL(/.*collections/);

    // ── 3. 点击"+ 新建"按钮 ─────────────────────────────
    await thinkDelay(page);
    // 寻找新建按钮（可能在左侧面板 toolbar 中）
    const createBtn = page.getByRole('button', { name: /新建/ });
    await expect(createBtn).toBeVisible({ timeout: 5000 });
    await createBtn.click();
    await thinkDelay(page);

    await expect(page.getByText('新建预制用例集')).toBeVisible();

    // ── 4. 填写 3 个字段 ───────────────────────────────
    // 集合名称 *
    const nameInput = page.locator('div').filter({ has: page.locator('label', { hasText: '集合名称' }) }).locator('input');
    await nameInput.fill(aiData.name);
    await humanDelay(page);

    // 描述
    const descTextarea = page.locator('div').filter({ has: page.locator('label', { hasText: '描述' }) }).locator('textarea');
    await descTextarea.fill(aiData.description);
    await humanDelay(page);

    // 标签（逗号分隔）
    const tagsInput = page.locator('div').filter({ has: page.locator('label', { hasText: '标签' }) }).locator('input');
    await tagsInput.fill(tagsStr);
    await humanDelay(page);

    // ── 5. 提交创建 ──────────────────────────────────────
    await page.getByRole('button', { name: '创建' }).click();
    await thinkDelay(page);

    // ── 6. 验证弹窗关闭 + 集合出现在列表中 ──────────────
    await expect(page.getByText('新建预制用例集')).not.toBeVisible({ timeout: 10000 });
    // 验证新集合在列表中可见
    await expect(page.getByText(aiData.name).first()).toBeVisible({ timeout: 10000 });
    console.log(`[验证] 预制用例集"${aiData.name}"已出现在列表中`);
  });
});
