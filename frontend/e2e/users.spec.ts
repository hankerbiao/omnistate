/**
 * 用户创建 E2E 测试
 *
 * 覆盖：AI 数据生成 → 导航到用户管理 → 点击"+ 新建"
 *       → 填写 5 个字段（含角色选择） → 提交 → 验证成功
 */
import { test, expect } from '@playwright/test';
import { loginAs, navigateTo, humanDelay, thinkDelay, closeDelay } from './helpers';
import { generateUserData } from './ai-helper';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('创建用户', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('AI 生成数据 → 打开新建弹窗 → 填写字段 → 提交创建 → 验证成功', async ({ page }) => {
    // ── 1. AI 生成测试数据 ──────────────────────────────
    const aiData = await generateUserData('E2E 自动测试创建的用户，用于验证用户管理功能');
    const password = `Test_${Date.now().toString().slice(-6)}`;
    console.log(`[AI] 生成用户ID: ${aiData.userId} (用户名: ${aiData.username})`);

    // ── 2. 登录 + 导航到用户管理 ────────────────────────
    await loginAs(page);
    await navigateTo(page, '用户管理');
    await expect(page.locator('.topbar__title')).toContainText('用户管理');
    await expect(page).toHaveURL(/.*users/);

    // ── 3. 点击"+ 新建"按钮 ─────────────────────────────
    await thinkDelay(page);
    await page.getByRole('button', { name: '+ 新建' }).click();
    await thinkDelay(page);

    await expect(page.getByText('新建用户')).toBeVisible();

    // ── 4. 填写表单字段 ─────────────────────────────────
    // 用户ID *
    const idInput = page.locator('div').filter({ has: page.locator('label', { hasText: '用户ID' }) }).locator('input');
    await idInput.fill(aiData.userId);
    await humanDelay(page);

    // 用户名 *
    const nameInput = page.locator('div').filter({ has: page.locator('label', { hasText: '用户名' }) }).locator('input');
    await nameInput.fill(aiData.username);
    await humanDelay(page);

    // 密码 *
    const pwdInput = page.locator('div').filter({ has: page.locator('label', { hasText: '密码' }) }).locator('input');
    await pwdInput.fill(password);
    await humanDelay(page);

    // 邮箱（可选）
    const emailInput = page.locator('div').filter({ has: page.locator('label', { hasText: '邮箱' }) }).locator('input');
    await emailInput.fill(aiData.email);
    await humanDelay(page);

    // ── 5. 选择初始角色（如果存在可选角色） ──────────────
    const roleCheckboxes = page.locator('input[type="checkbox"]');
    const roleCount = await roleCheckboxes.count();
    if (roleCount > 0) {
      // 勾选第一个角色
      await roleCheckboxes.first().click();
      await humanDelay(page);
      console.log(`[测试] 已勾选初始角色`);
    }

    // ── 6. 提交创建 ──────────────────────────────────────
    // 等待创建按钮可用（必填字段已填）
    await expect(page.getByRole('button', { name: '创建' })).toBeEnabled({ timeout: 5000 });
    await page.getByRole('button', { name: '创建' }).click();
    await thinkDelay(page);

    // ── 7. 验证弹窗关闭 + 用户出现在列表中 ──────────────
    await expect(page.getByText('新建用户')).not.toBeVisible({ timeout: 10000 });
    // 新创建的用户应出现在用户列表或搜索中
    await expect(page.getByText(aiData.userId).first()).toBeVisible({ timeout: 10000 });
    console.log(`[验证] 用户"${aiData.userId}"已出现在列表中`);
  });
});
