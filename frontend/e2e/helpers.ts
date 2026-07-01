import type { Page, TestInfo } from '@playwright/test';
import { test as base } from '@playwright/test';

// ──────────────────────────────────────────────
//  人工行为模拟
// ──────────────────────────────────────────────

/** 模拟人工操作间隔（150~350ms 随机），让测试更接近真实用户行为 */
export async function humanDelay(page: Page) {
  const ms = 150 + Math.floor(Math.random() * 200);
  await page.waitForTimeout(ms);
}

/** 稍长一点的思考停顿（400~700ms），适合页面切换或操作前后 */
export async function thinkDelay(page: Page) {
  const ms = 400 + Math.floor(Math.random() * 300);
  await page.waitForTimeout(ms);
}

// ──────────────────────────────────────────────
//  全局 afterEach — 每个用例结束后等待 1s
// ──────────────────────────────────────────────

/**
 * 在每个 test 文件中调用此 hook，确保用例执行完毕后等待 1s 再关闭页面。
 * 用法：放在 describe 块外（全局），参考各 spec 文件。
 */
export async function closeDelay(page: Page, testInfo: TestInfo) {
  // 仅在用例通过或失败时等待（跳过进行中的）
  await page.waitForTimeout(1000);
}

// ──────────────────────────────────────────────
//  测试用户定义（与前端 config/users.ts 一致）
// ──────────────────────────────────────────────
export const TEST_USERS = {
  admin:    { userId: 'admin',    password: 'Test@123', label: '管理员',   role: 'ADMIN' },
  tpm:      { userId: 'tpm',      password: 'Test@123', label: '项目经理', role: 'TPM' },
  reviewer: { userId: 'reviewer', password: 'Test@123', label: '审核人',   role: 'REVIEWER' },
  dev:      { userId: 'dev',      password: 'Test@123', label: '开发人员', role: 'MANUAL_DEV' },
  qa:       { userId: 'qa',       password: 'Test@123', label: '质量保证', role: 'QA' },
  tester:   { userId: 'tester',   password: 'Test@123', label: '测试人员', role: 'TESTER' },
} as const;

export type TestUserRole = keyof typeof TEST_USERS;

// ── 密码常量 ─────────────────────────────────────────────────
/** 所有预置用户的统一密码 */
export const DEFAULT_PASSWORD = 'Test@123';

/** 默认登录页预填的用户名 */
export const DEFAULT_USER_ID = 'admin';

// ──────────────────────────────────────────────
//  Mock 工厂函数
// ──────────────────────────────────────────────

/** Mock login 成功响应 */
export function mockLoginResponse(userId: string = DEFAULT_USER_ID) {
  return {
    code: 0,
    data: {
      access_token: `mock-jwt-token-${userId}-${Date.now()}`,
      token_type: 'bearer',
      user: { user_id: userId, username: userId },
    },
  };
}

/** Mock 当前用户信息 */
export function mockCurrentUserResponse(userId: string, username?: string) {
  return {
    code: 0,
    data: {
      user_id: userId,
      username: username ?? userId,
      role_ids: [],
      is_active: true,
    },
  };
}

/** Mock 权限列表 */
export function mockPermissionsResponse(permissions: string[]) {
  return {
    code: 0,
    data: { permissions },
  };
}

// ──────────────────────────────────────────────
//  权限预设
// ──────────────────────────────────────────────

/** 默认的 ADMIN 用户权限（所有页面可见） */
export function adminPermissions(): string[] {
  return [
    'search:global',
    'requirements:read',
    'test_cases:read',
    'collections:read',
    'projects:read',
    'execution_agents:read',
    'execution_plans:read',
    'case_governance:read',
    'execution_tasks:read',
    'nav:dashboard:view',
    'users:read',
    'roles:read',
    'permissions:read',
    'catalog:labs:manage',
    'system:config',
  ];
}

/** TPM 权限（无系统管理权限） */
export function tpmPermissions(): string[] {
  return [
    'search:global',
    'requirements:read',
    'test_cases:read',
    'collections:read',
    'projects:read',
    'execution_agents:read',
    'execution_plans:read',
    'case_governance:read',
    'execution_tasks:read',
    'nav:dashboard:view',
  ];
}

/** 受限用户的权限（只能看部分页面） */
export function testerPermissions(): string[] {
  return [
    'test_cases:read',
    'execution_plans:read',
    'execution_tasks:read',
  ];
}

// ──────────────────────────────────────────────
//  通用 Mock API 辅助
// ──────────────────────────────────────────────

/**
 * 为登录页面的关键 API 设置 Mock 响应。
 * 适用于需要通过 Playwright route 拦截的场景。
 */
export async function mockAuthApis(page: Page, userId: string = DEFAULT_USER_ID, permissions: string[] = adminPermissions()) {
  // Mock 登录接口
  await page.route('**/api/v1/auth/login', async (route) => {
    const body = JSON.stringify(mockLoginResponse(userId));
    await route.fulfill({ status: 200, contentType: 'application/json', body });
  });

  // Mock 当前用户信息接口
  await page.route('**/api/v1/auth/users/me', async (route) => {
    const body = JSON.stringify(mockCurrentUserResponse(userId, userId));
    await route.fulfill({ status: 200, contentType: 'application/json', body });
  });

  // Mock 权限接口
  await page.route('**/api/v1/auth/users/me/permissions', async (route) => {
    const body = JSON.stringify(mockPermissionsResponse(permissions));
    await route.fulfill({ status: 200, contentType: 'application/json', body });
  });
}

/**
 * Mock 所有非认证 API 返回空数据（避免网络错误干扰测试）
 */
export async function mockAllOtherApis(page: Page, excludePaths: string[] = []) {
  await page.route('**/api/v1/**', async (route) => {
    const url = route.request().url();
    // 跳过认证相关的路由（应由 mockAuthApis 处理）
    if (
      url.includes('/auth/login') ||
      url.includes('/auth/users/me') ||
      url.includes('/auth/users/me/permissions')
    ) {
      await route.continue();
      return;
    }
    // 跳过 excludePaths 中指定的路径
    for (const exclude of excludePaths) {
      if (url.includes(exclude)) {
        await route.continue();
        return;
      }
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, data: [] }),
    });
  });
}

// ──────────────────────────────────────────────
//  认证辅助（本地存储注入）
// ──────────────────────────────────────────────

/**
 * 通过注入 localStorage 来跳过登录流程，直接进入已认证状态。
 * 这比走完整登录流程更快，适合不需要测试登录功能的场景。
 * 使用前必须先调用 page.goto()。
 */
export async function authenticateViaStorage(
  page: Page,
  userId: string = DEFAULT_USER_ID,
) {
  const token = `mock-jwt-token-${userId}`;

  await page.evaluate(
    ({ token, userId }) => {
      localStorage.setItem('jwt_token', token);
      localStorage.setItem('saved_user_id', userId);
    },
    { token, userId },
  );

  // Mock 认证后页面加载时发起的请求
  await page.route('**/api/v1/auth/users/me', async (route) => {
    const body = JSON.stringify(mockCurrentUserResponse(userId));
    await route.fulfill({ status: 200, contentType: 'application/json', body });
  });

  await page.route('**/api/v1/auth/users/me/permissions', async (route) => {
    const body = JSON.stringify(mockPermissionsResponse(adminPermissions()));
    await route.fulfill({ status: 200, contentType: 'application/json', body });
  });
}

// ──────────────────────────────────────────────
//  UI 交互辅助
// ──────────────────────────────────────────────

/** 在登录页填写表单并提交（使用默认凭证） */
export async function loginAs(page: Page, userId: string = DEFAULT_USER_ID, password: string = DEFAULT_PASSWORD) {
  await page.goto('/');
  await humanDelay(page);
  await page.locator('#user_id').fill(userId);
  await humanDelay(page);
  await page.locator('#password').fill(password);
  await humanDelay(page);
  await page.getByRole('button', { name: /^登录$/ }).click();
  await thinkDelay(page);
}

/** 等待 Topbar 标题出现，确认页面加载完成 */
export async function waitForPageLoaded(page: Page, titleText?: string) {
  if (titleText) {
    await page.locator('.topbar__title').filter({ hasText: titleText }).waitFor({ timeout: 10000 });
  } else {
    await page.locator('.topbar__title').first().waitFor({ timeout: 10000 });
  }
  await humanDelay(page);
}

/** 点击侧边栏导航项 */
export async function navigateTo(page: Page, navLabel: string) {
  await thinkDelay(page);
  await page.locator('.sidebar__item').filter({ hasText: navLabel }).click();
  await thinkDelay(page);
  await page.locator('.topbar__title').first().waitFor({ timeout: 10000 });
  await humanDelay(page);
}

/** 清空 localStorage 并返回登录页 */
export async function resetToLogin(page: Page) {
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
}

/**
 * 以认证状态直接导航到指定页面
 * 使用 authenticateViaStorage 跳过登录流程
 */
export async function gotoAsAuthenticated(page: Page, url: string, userId: string = DEFAULT_USER_ID) {
  await page.goto('/');
  await authenticateViaStorage(page, userId);
  await page.goto(url);
  await waitForPageLoaded(page);
}
