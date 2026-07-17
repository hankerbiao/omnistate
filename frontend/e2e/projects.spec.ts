/**
 * 项目创建 E2E 测试
 *
 * 覆盖：AI 数据生成 → 导航到项目 → 打开新建弹窗 → 填写 8 个字段
 *       → 提交 → 验证弹窗关闭 + 项目出现在列表中
 */
import { test, expect } from '@playwright/test';
import { loginAs, navigateTo, humanDelay, thinkDelay, closeDelay } from './helpers';
import { generateProjectData } from './ai-helper';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('创建项目', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('AI 生成数据 → 打开新建弹窗 → 填写全部字段 → 提交创建 → 验证成功', async ({ page }) => {
    // ── 1. AI 生成测试数据 ──────────────────────────────
    const aiData = await generateProjectData(
      '新项目用来做 E2E 自动化回归测试'
    );
    // ai-helper 内部已追加时间戳
    console.log(`[AI] 生成项目名称: ${aiData.name} (KEY: ${aiData.key})`);

    // ── 2. 登录 + 导航到项目页面 ────────────────────────
    await loginAs(page);
    await navigateTo(page, '项目');
    await expect(page.locator('.topbar__title')).toContainText('项目');
    await expect(page).toHaveURL(/.*projects/);

    // ── 3. 点击"+ 新建"按钮 ─────────────────────────────
    await thinkDelay(page);
    await page.getByRole('button', { name: '+ 新建' }).click();
    await thinkDelay(page);

    await expect(page.getByText('新建项目')).toBeVisible();

    // ── 4. 填写 8 个字段（2 列网格） ───────────────────
    // 名称 *
    const nameInput = page.locator('div').filter({ has: page.locator('label', { hasText: '名称' }) }).locator('input');
    await nameInput.fill(aiData.name);
    await humanDelay(page);

    // 标识 *（自动转大写）
    const keyInput = page.locator('div').filter({ has: page.locator('label', { hasText: '标识' }) }).locator('input');
    await keyInput.fill(aiData.key.slice(0, 10));
    await humanDelay(page);

    // 描述（跨 2 列）
    const descTextarea = page.locator('div').filter({ has: page.locator('label', { hasText: '描述' }) }).locator('textarea');
    await descTextarea.fill(aiData.description);
    await humanDelay(page);

    // 优先级（select）
    await page.locator('select').first().selectOption(aiData.priority);
    await humanDelay(page);

    // 目标版本
    const versionInput = page.locator('div').filter({ has: page.locator('label', { hasText: '目标版本' }) }).locator('input');
    await versionInput.fill(aiData.version);
    await humanDelay(page);

    // 计划开始 / 计划结束（date）
    const dateInputs = page.locator('input[type="date"]');
    await dateInputs.nth(0).fill('2026-07-15');
    await humanDelay(page);
    await dateInputs.nth(1).fill('2026-08-15');
    await humanDelay(page);

    // 标签（逗号分隔，跨 2 列）
    const tagsInput = page.locator('div').filter({ has: page.locator('label', { hasText: '标签' }) }).locator('input');
    await tagsInput.fill('回归, 冒烟, E2E');
    await humanDelay(page);

    // ── 5. 提交创建 ──────────────────────────────────────
    await page.getByRole('button', { name: '保存' }).click();
    await thinkDelay(page);

    // ── 6. 验证弹窗关闭 + 项目出现在列表中 ──────────────
    await expect(page.getByText('新建项目')).not.toBeVisible({ timeout: 10000 });
    // 验证新创建的项目在列表中（按名称匹配）
    await expect(page.getByText(aiData.name).first()).toBeVisible({ timeout: 10000 });
    console.log(`[验证] 项目"${aiData.name}"已出现在列表中`);
  });
});
