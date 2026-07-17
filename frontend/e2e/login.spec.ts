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

test.describe('登录认证核心用例', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('登录页应正常加载，表单有默认值，支持保存密码勾选', async ({ page }) => {
    await page.goto('/');
    await humanDelay(page);

    await expect(page.locator('h1')).toContainText('DML Sentio');
    await expect(page.getByText('测试管理平台')).toBeVisible();

    await expect(page.locator('#user_id')).toHaveValue(DEFAULT_USER_ID);
    await expect(page.locator('#password')).toHaveValue(DEFAULT_PASSWORD);

    await expect(page.getByText('保存密码')).toBeVisible();
    await expect(page.locator('input[type="checkbox"]')).not.toBeChecked();
  });

  test('使用正确凭据成功登录 → 跳转仪表盘 → 写入 token → 退出登录', async ({ page }) => {
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill(DEFAULT_USER_ID);
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();

    await expect(page.locator('.topbar')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('.sidebar')).toBeVisible();

    const token = await page.evaluate(() => localStorage.getItem('jwt_token'));
    expect(token).toBeTruthy();

    await thinkDelay(page);
    await page.getByRole('button', { name: '退出' }).click();
    await expect(page.locator('#user_id')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('h1')).toContainText('DML Sentio');

    const clearedToken = await page.evaluate(() => localStorage.getItem('jwt_token'));
    expect(clearedToken).toBeNull();
  });

  test('凭据错误应显示错误提示', async ({ page }) => {
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill('wrong_user');
    await humanDelay(page);
    await page.locator('#password').fill('bad_password');
    await humanDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();

    await expect(page.getByText('登录失败，请检查用户名和密码')).toBeVisible({ timeout: 10000 });
  });

  test('已有合法 token 刷新保持登录，无 token 回退登录页', async ({ page }) => {
    // 先正常登录获取 token
    await page.goto('/');
    await page.locator('#user_id').fill(DEFAULT_USER_ID);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page.locator('.topbar')).toBeVisible({ timeout: 15000 });

    // 刷新页面应保持登录
    await page.reload();
    await expect(page.locator('.topbar')).toBeVisible({ timeout: 10000 });

    // 清除 token 后刷新应回到登录页
    await page.evaluate(() => localStorage.removeItem('jwt_token'));
    await page.reload();
    await expect(page.locator('#user_id')).toBeVisible({ timeout: 10000 });
  });
});
