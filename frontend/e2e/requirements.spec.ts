import { test, expect } from '@playwright/test';
import {
  DEFAULT_USER_ID,
  DEFAULT_PASSWORD,
  humanDelay,
  thinkDelay,
  closeDelay,
} from './helpers';
import { generateRequirementData } from './ai-helper';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('创建测试需求完整流程', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('AI 生成数据 → 打开新建表单 → 填写全部字段 → 提交创建 → 验证成功', async ({ page }) => {
    // ── 1. AI 生成测试数据 ──────────────────────────────
    const aiData = await generateRequirementData(
      '用户登录模块回归测试，覆盖用户名密码登录、SSO单点登录、Token刷新等场景'
    );
    // 追加时间戳保证标题唯一，避免后端"已存在相同标题"错误
    aiData.title = `${aiData.title}-${Date.now()}`;
    console.log(`[AI] 生成需求标题: ${aiData.title} (分类: ${aiData.category})`);

    // ── 2. 登录（走真实后端） ────────────────────────────
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill(DEFAULT_USER_ID);
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page).toBeDefined();
    await thinkDelay(page);

    // ── 3. 导航到需求页面 ────────────────────────────────
    await page.locator('.sidebar__item').filter({ hasText: '测试用例编写需求' }).click();
    await thinkDelay(page);
    await expect(page.locator('.topbar__title')).toContainText('测试用例编写需求');
    await expect(page).toHaveURL(/.*requirements/);

    // ── 4. 点击"+ 新建"按钮 ──────────────────────────────
    await thinkDelay(page);
    await page.getByRole('button', { name: '+ 新建' }).click();
    await thinkDelay(page);

    await expect(page.getByText('创建测试用例编写需求')).toBeVisible();
    await expect(page.getByText('填写需求信息，后续将自动关联工作流与测试用例')).toBeVisible();

    // ── 5. 填写基础信息（AI 生成数据） ──────────────────
    await page.locator('input[name="title"]').fill(aiData.title);
    await humanDelay(page);

    // 优先级
    await page.locator('button').filter({ hasText: aiData.priority }).first().click();
    await humanDelay(page);

    // 需求分类
    await page.locator('select[name="category"]').selectOption(aiData.category);
    await humanDelay(page);

    // 验收标准
    await page.locator('textarea[name="acceptance_criteria"]').fill(aiData.acceptanceCriteria);
    await humanDelay(page);

    // ── 6. 填写计划时间 ──────────────────────────────────
    const dateInputs = page.locator('input[type="date"]');
    await dateInputs.nth(0).fill('2026-07-01');
    await humanDelay(page);
    await dateInputs.nth(1).fill('2026-07-15');
    await humanDelay(page);

    // ── 7. AI 推荐标签（作为自定义标签输入） ────────────
    for (const tag of aiData.tags) {
      await page.locator('input[placeholder="自定义标签，回车添加"]').fill(tag);
      await humanDelay(page);
      await page.locator('button').filter({ hasText: '添加' }).click();
      await humanDelay(page);
    }

    // ── 8. 填写结构化描述（AI 生成内容） ──────────────
    await page.getByPlaceholder('为什么需要这个需求？业务场景是什么？').fill(aiData.background);
    await humanDelay(page);
    await page.getByPlaceholder('具体要测哪些功能？变更点是什么？').fill(aiData.functional);
    await humanDelay(page);
    await page.getByPlaceholder('环境/数据/配置有什么要求？').fill(aiData.precondition);
    await humanDelay(page);
    await page.getByPlaceholder('重点验证哪些方面？边界情况？').fill(aiData.testFocus);
    await thinkDelay(page);

    // ── 9. 提交创建 ──────────────────────────────────────
    await page.getByRole('button', { name: '创建需求' }).click();

    // 验证创建成功
    await expect(page.getByText(/需求已创建/)).toBeVisible({ timeout: 15000 });

    // 验证后处理按钮
    await expect(page.getByRole('button', { name: 'AI 生成用例' })).toBeVisible();
    await expect(page.getByRole('button', { name: '完成' })).toBeVisible();

    // 关闭模态框
    await humanDelay(page);
    await page.getByRole('button', { name: '完成' }).click();
    await thinkDelay(page);

    await expect(page.getByText('创建测试用例编写需求')).not.toBeVisible();
  });
});
