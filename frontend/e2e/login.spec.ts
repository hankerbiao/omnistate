import { test, expect } from '@playwright/test';

test.describe('登录认证流程', () => {
  test('应显示登录页面并成功登录', async ({ page }) => {
    // 访问首页，应重定向到登录页
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /登录/i })).toBeVisible();

    // 填写登录表单
    await page.getByLabel(/用户名/i).fill('admin001');
    await page.getByLabel(/密码/i).fill('Admin@123');
    await page.getByRole('button', { name: /登录/i }).click();

    // 登录成功后应跳转到仪表盘
    await expect(page).toHaveURL(/.*dashboard/);
  });

  test('应拒绝无效凭证', async ({ page }) => {
    await page.goto('/login');

    await page.getByLabel(/用户名/i).fill('invalid_user');
    await page.getByLabel(/密码/i).fill('wrong_password');
    await page.getByRole('button', { name: /登录/i }).click();

    // 应显示错误提示
    await expect(page.getByText(/登录失败|无效|错误/i)).toBeVisible();
  });
});

test.describe('导航权限验证', () => {
  test('ADMIN 角色应看到所有导航项', async ({ page }) => {
    // 先以管理员身份登录
    await page.goto('/login');
    await page.getByLabel(/用户名/i).fill('admin001');
    await page.getByLabel(/密码/i).fill('Admin@123');
    await page.getByRole('button', { name: /登录/i }).click();

    // 验证管理员能看到的导航项
    await expect(page.getByRole('link', { name: /仪表盘/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /执行计划/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /系统配置/i })).toBeVisible();
  });

  test('TESTER 角色应仅看到授权导航项', async ({ page }) => {
    // 模拟 TESTER 角色登录
    await page.goto('/login');
    await page.getByLabel(/用户名/i).fill('tester001');
    await page.getByLabel(/密码/i).fill('Tester@123');
    await page.getByRole('button', { name: /登录/i }).click();

    // 验证受限导航项不可见
    await expect(page.getByRole('link', { name: /仪表盘/i })).toBeVisible();
    // 系统配置应对 TESTER 不可见
    await expect(page.getByRole('link', { name: /系统配置/i })).not.toBeVisible();
  });
});
