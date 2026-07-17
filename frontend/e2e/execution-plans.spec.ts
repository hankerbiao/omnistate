/**
 * 执行计划创建 E2E 测试
 *
 * 覆盖：AI 数据生成 → 导航到执行计划 → 打开 4 步创建向导
 *       → Step 1 填写基本信息 → Step 2 选择/搜索用例
 *       → Step 3 分配执行人 → Step 4 排期确认 → 创建 → 验证
 *
 * 注意：如果系统无可用测试用例，测试会优雅跳过步骤 2-3
 */
import { test, expect } from '@playwright/test';
import { loginAs, navigateTo, humanDelay, thinkDelay, closeDelay } from './helpers';
import { generatePlanData } from './ai-helper';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('创建执行计划', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('AI 生成数据 → 4 步向导填写 → 创建计划 → 验证成功', async ({ page }) => {
    // ── 1. AI 生成测试数据 ──────────────────────────────
    const aiData = await generatePlanData(
      'Sprint 3 E2E 自动回归测试计划，覆盖核心功能回归'
    );
    console.log(`[AI] 生成计划名称: ${aiData.title}`);

    // ── 2. 登录 + 导航到执行计划 ────────────────────────
    await loginAs(page);
    await navigateTo(page, '执行计划');
    await expect(page.locator('.topbar__title')).toContainText('执行计划');
    await expect(page).toHaveURL(/.*execution-plans/);

    // ── 3. 点击"+ 新建计划"按钮 ─────────────────────────
    await thinkDelay(page);
    await page.getByRole('button', { name: '新建计划' }).click();
    await thinkDelay(page);

    await expect(page.getByText('新建执行计划')).toBeVisible();

    // ══════════════════════════════════════════════════════════
    //  Step 1：基本信息
    // ══════════════════════════════════════════════════════════
    // 计划名称 *
    const titleInput = page.locator('input').first();
    await titleInput.fill(aiData.title);
    await humanDelay(page);

    // 描述
    const descTextarea = page.locator('textarea').first();
    await descTextarea.fill(aiData.description);
    await humanDelay(page);

    // 计划周期（如果存在 DateRangePicker）
    const dateInputs = page.locator('input[type="text"]').filter({ has: page.locator('[value=""]') });
    // 尝试填写日期
    const dateFields = page.locator('input[type="text"]');
    const dateCount = await dateFields.count();
    if (dateCount >= 2) {
      await dateFields.nth(0).fill('2026-07-15');
      await humanDelay(page);
      await dateFields.nth(1).fill('2026-07-30');
      await humanDelay(page);
    }

    // 点击"下一步"
    await page.getByRole('button', { name: '下一步' }).click();
    await thinkDelay(page);
    console.log('[向导] Step 1 完成 → 进入 Step 2');

    // ══════════════════════════════════════════════════════════
    //  Step 2：选择用例
    // ══════════════════════════════════════════════════════════
    // 等待用例列表加载
    await page.waitForTimeout(2000);

    // 检查是否有可用用例
    const caseItems = page.locator('[class*="case-item"], [class*="row"], [role="option"]');
    const caseCount = await caseItems.count().catch(() => 0);

    if (caseCount === 0) {
      // 尝试搜索
      const searchInput = page.locator('input[placeholder*="搜索"]').first();
      if (await searchInput.isVisible().catch(() => false)) {
        await searchInput.fill('登录');
        await humanDelay(page);
        await page.waitForTimeout(1000);
      }

      const hasCases = await caseItems.count().catch(() => 0) > 0;
      if (hasCases) {
        // 勾选第一个用例
        const checkbox = page.locator('input[type="checkbox"]').first();
        if (await checkbox.isVisible().catch(() => false)) {
          await checkbox.click();
          await humanDelay(page);
        }
      } else {
        // 没有可用用例 — 无法创建计划，跳过
        console.warn('[跳过] 系统无可用测试用例，无法完成计划创建');
        test.skip();
        return;
      }
    } else {
      // 有可见用例，勾选第一个
      const firstCheckbox = page.locator('input[type="checkbox"]').first();
      if (await firstCheckbox.isVisible({ timeout: 3000 }).catch(() => false)) {
        await firstCheckbox.click();
        await humanDelay(page);
      }
    }

    // 点击"下一步"
    await page.getByRole('button', { name: '下一步' }).click();
    await thinkDelay(page);
    console.log('[向导] Step 2 完成 → 进入 Step 3');

    // ══════════════════════════════════════════════════════════
    //  Step 3：分配执行人
    // ══════════════════════════════════════════════════════════
    // 默认已选中当前用户（admin），直接下一步
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: '下一步' }).click();
    await thinkDelay(page);
    console.log('[向导] Step 3 完成 → 进入 Step 4');

    // ══════════════════════════════════════════════════════════
    //  Step 4：排期确认 → 创建计划
    // ══════════════════════════════════════════════════════════
    // 验证概览卡片显示了计划名称
    await expect(page.getByText(aiData.title).first()).toBeVisible({ timeout: 5000 });
    console.log('[向导] Step 4 概览确认');

    // 点击"创建计划"
    await page.getByRole('button', { name: '创建计划' }).click();

    // ══════════════════════════════════════════════════════════
    //  验证
    // ══════════════════════════════════════════════════════════
    // 等待弹窗关闭 + 计划出现在列表中
    await expect(page.getByText('新建执行计划')).not.toBeVisible({ timeout: 15000 });
    // 侧边栏计划列表中应显示新创建的计划
    await expect(page.getByText(aiData.title).first()).toBeVisible({ timeout: 10000 });
    console.log(`[验证] 执行计划"${aiData.title}"已出现在列表中`);
  });
});
