import { test, expect } from '@playwright/test';
import {
  loginAs,
  navigateTo,
  humanDelay,
  thinkDelay,
  closeDelay,
} from './helpers';
import { generateRequirementData, generateTestCaseData } from './ai-helper';

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
    // ai-helper 内部已追加时间戳，无需重复
    console.log(`[AI] 生成需求标题: ${aiData.title} (分类: ${aiData.category})`);

    // ── 2. 登录 + 导航到需求页面 ────────────────────────
    await loginAs(page);
    await navigateTo(page, '测试用例编写需求');
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

    // ── 10. 通过 API 创建关联测试用例 ──────────────────
    const tcData = await generateTestCaseData(
      `针对需求"${aiData.title}"的测试用例，覆盖基本功能验证`
    );
    // ai-helper 内部已追加时间戳
    console.log(`[AI] 生成用例标题: ${tcData.title}`);

    const apiResult = await page.evaluate(async (data: {
      reqTitle: string;
      caseTitle: string;
      priority: string;
      background: string;
    }) => {
      const baseUrl = 'http://localhost:8000/api/v1';
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`,
      };

      // 1. 按标题查找刚创建的需求
      const reqsRes = await fetch(`${baseUrl}/requirements?limit=50`, { headers });
      const reqs = await reqsRes.json();
      const req = reqs.data?.find((r: any) => r.title === data.reqTitle);
      if (!req?.req_id) return { error: '未找到刚创建的需求', reqTitle: data.reqTitle };

      // 2. 获取可用 Lab
      const labsRes = await fetch(`${baseUrl}/catalog/labs?active_only=true`, { headers });
      const labs = await labsRes.json();
      const labId = labs.data?.[0]?.lab_id;
      if (!labId) return { error: '无可用 Lab', reqId: req.req_id };

      // 3. 创建测试用例
      const createRes = await fetch(`${baseUrl}/test-cases`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ref_req_id: req.req_id,
          lab_id: labId,
          catalog_path: ['默认'],
          title: data.caseTitle,
          priority: data.priority,
          steps: [{
            step_id: 'step-1',
            name: '验证基本功能',
            action: '执行测试步骤',
            expected: '结果符合预期',
          }],
          tags: ['E2E'],
          pre_condition: data.background.slice(0, 100),
        }),
      });
      const createData = await createRes.json();
      return {
        reqId: req.req_id,
        labId,
        caseId: createData.data?.case_id,
        code: createData.code,
        error: createData.code !== 0 ? createData.message || '创建失败' : undefined,
      };
    }, {
      reqTitle: aiData.title,
      caseTitle: tcData.title,
      priority: tcData.priority,
      background: `${aiData.background}\n${aiData.functional}`,
    });

    expect(apiResult.error).toBeUndefined();
    expect(apiResult.caseId).toBeDefined();
    console.log(`[测试] 测试用例创建成功: ${apiResult.caseId}`);

    // ── 11. 在 UI 中验证用例出现在需求详情中 ──────────
    // 切换到"测试用例" tab
    await page.getByRole('button', { name: /测试用例/ }).click();
    await thinkDelay(page);

    // 验证新创建的用例在列表中可见
    await expect(page.getByText(tcData.title)).toBeVisible({ timeout: 10000 });
    console.log('[测试] 测试用例已在需求详情中显示');
  });
});
