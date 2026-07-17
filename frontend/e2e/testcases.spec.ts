import { test, expect } from '@playwright/test';
import {
  loginAs,
  navigateTo,
  humanDelay,
  thinkDelay,
  closeDelay,
} from './helpers';
import { generateTestCaseData } from './ai-helper';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('创建手工用例完整流程', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('AI 生成数据 → 打开新建表单 → 填写全部字段 → 提交创建 → 验证成功', async ({ page }) => {
    test.setTimeout(120000); // 创建用例涉及 AI 调用和多步骤表单，放宽整体超时
    // ── 1. AI 生成测试数据 ──────────────────────────────
    const aiData = await generateTestCaseData(
      '用户登录功能回归测试，覆盖用户名密码登录、验证码校验、登录状态保持等场景'
    );
    // ai-helper 内部已追加时间戳，无需重复
    console.log(`[AI] 生成用例标题: ${aiData.title} (优先级: ${aiData.priority}, 分类: ${aiData.category})`);

    // ── 2. 登录 + 导航到用例看板 ────────────────────────
    await loginAs(page);
    await navigateTo(page, '用例看板');
    await expect(page.locator('.topbar__title')).toContainText('用例看板');
    await expect(page).toHaveURL(/.*test-cases/);

    // ── 4. 点击「+ 手工」按钮 ───────────────────────────
    await thinkDelay(page);
    await page.getByRole('button', { name: '创建手工用例' }).click();
    await thinkDelay(page);

    // 验证弹窗已打开
    await expect(page.locator('.modal__title')).toHaveText('创建测试用例');
    await expect(page.getByText('先确定所属目录，再填写用例详情')).toBeVisible();

    // ── 5. 填写所属目录（Lab + 路径段） ────────────────
    // 选择 Lab（等待选项加载，选择第一个非空选项）
    const labSelect = page.getByRole('combobox', { name: /^实验室.*Lab/ });
    const labOptions = labSelect.locator('option');
    // 等待至少 2 个选项（占位 + 真实选项），选项可能异步加载
    await expect(async () => {
      expect(await labOptions.count()).toBeGreaterThanOrEqual(2);
    }).toPass({ timeout: 10000 });
    console.log(`[Debug] Lab combobox 选项数: ${await labOptions.count()}`);
    const firstLabValue = await labOptions.nth(1).getAttribute('value');
    await labSelect.selectOption(firstLabValue || '');
    await humanDelay(page);

    // 填写路径段
    await page.getByPlaceholder('路径段 1').fill(aiData.category || '功能测试');
    await humanDelay(page);

    // ── 6. 填写用例名称 ──────────────────────────────────
    await page.locator('input[name="title"]').fill(aiData.title);
    await humanDelay(page);

    // ── 7. 选择优先级（P0-P3 → 紧急/高/中/低） ──────────
    const PRIORITY_MAP: Record<string, string> = { P0: '紧急', P1: '高', P2: '中', P3: '低' };
    const priorityLabel = PRIORITY_MAP[aiData.priority.toUpperCase()] || aiData.priority;
    await page.getByRole('group', { name: '优先级' }).getByRole('button', { name: priorityLabel }).click();
    await humanDelay(page);

    // ── 8. 展开高级选项 ──────────────────────────────────
    await page.locator('button').filter({ hasText: '高级选项' }).click();
    await humanDelay(page);
    await expect(page.getByText('关联需求')).toBeVisible();

    // ── 9. 填写前置条件 ──────────────────────────────────
    if (aiData.precondition) {
      await page.locator('textarea[name="pre_condition"]').fill(aiData.precondition);
      await humanDelay(page);
    }

    // ── 10. 添加标签 ────────────────────────────────────
    for (const tag of aiData.tags) {
      await page.locator('input[placeholder="输入标签后回车或点击添加"]').fill(tag);
      await humanDelay(page);
      await page.getByRole('button', { name: '添加', exact: true }).click();
      await humanDelay(page);
    }

    // ── 11. 填写步骤 ────────────────────────────────────
    await page.getByRole('tab', { name: '步骤' }).click();
    await humanDelay(page);

    const stepLines = aiData.steps
      .replace(/；/g, '\n') // AI 有时用分号分隔步骤
      .split('\n')
      .map(s => s.trim())
      .filter(Boolean);
    for (let i = 0; i < stepLines.length; i++) {
      await page.getByRole('button', { name: /添加步骤/ }).click();
      await humanDelay(page);

      // 去掉 "1. ", "2. " 等编号前缀
      const cleanText = stepLines[i].replace(/^\d+\s*[\.、\)\s]\s*/, '').trim();

      // 步骤标题
      await page.locator('input[placeholder="如：安装内存、读取 SPD"]').fill(cleanText.slice(0, 50));
      await humanDelay(page);

      // 动作
      await page.locator('textarea[placeholder="描述具体操作步骤"]').fill(cleanText);
      await humanDelay(page);

      // 期望（最后一个步骤使用 AI 生成的预期结果）
      const expected = i === stepLines.length - 1 ? aiData.expectedResult : '步骤执行通过';
      await page.locator('textarea[placeholder="描述可观测的通过标准"]').fill(expected);
      await humanDelay(page);
    }

    // ── 12. 提交创建 ─────────────────────────────────────
    await thinkDelay(page);
    await page.getByRole('button', { name: '创建测试用例' }).click();

    // 短暂等待后检查是否有错误提示
    await page.waitForTimeout(2000);
    const errorMsg = page.locator('.error-message');
    if (await errorMsg.isVisible().catch(() => false)) {
      console.error(`[错误] 表单提交失败: ${await errorMsg.textContent()}`);
    }

    // 验证创建成功：弹窗关闭，表单消失（创建接口含步骤数据较慢，给充足时间）
    await expect(page.locator('.modal__title')).not.toBeVisible({ timeout: 60000 });
    await expect(page.getByRole('button', { name: '创建测试用例' })).not.toBeVisible();

    // ── 12. 可选：验证看板页面刷新后可看到新用例 ────
    // 由于创建成功后页面调用了 fetchAll() 刷新列表，
    // 列表中出现新创建的用例标题即代表端到端流程完整
    await expect(page.getByText(aiData.title).first()).toBeVisible({ timeout: 10000 });
    console.log(`[验证] 用例"${aiData.title}"已出现在看板列表中`);
  });
});
