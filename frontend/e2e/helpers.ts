import type { Page, TestInfo } from '@playwright/test';

// ──────────────────────────────────────────────
//  常量
// ──────────────────────────────────────────────

/** 所有预置用户的统一密码 */
export const DEFAULT_PASSWORD = 'Test@123';

/** 默认登录页预填的用户名 */
export const DEFAULT_USER_ID = 'admin';

// ──────────────────────────────────────────────
//  人工行为模拟
// ──────────────────────────────────────────────

/** 模拟人工操作间隔（150~350ms 随机） */
export async function humanDelay(page: Page) {
  await page.waitForTimeout(150 + Math.floor(Math.random() * 200));
}

/** 稍长停顿（400~700ms），适合页面切换或操作前后 */
export async function thinkDelay(page: Page) {
  await page.waitForTimeout(400 + Math.floor(Math.random() * 300));
}

/** afterEach hook — 每个用例结束后等待 1s */
export async function closeDelay(page: Page, _testInfo: TestInfo) {
  await page.waitForTimeout(1000);
}

// ──────────────────────────────────────────────
//  UI 交互辅助
// ──────────────────────────────────────────────

/** 在登录页填写表单并提交 */
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

/** 点击侧边栏导航项并等待页面加载 */
export async function navigateTo(page: Page, navLabel: string) {
  await thinkDelay(page);
  await page.locator('.sidebar__item').filter({ hasText: navLabel }).click();
  await thinkDelay(page);
  await page.locator('.topbar__title').first().waitFor({ timeout: 10000 });
  await humanDelay(page);
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
