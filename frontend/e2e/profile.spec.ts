import { test, expect } from '@playwright/test';
import {
  loginAs,
  humanDelay,
  thinkDelay,
  closeDelay,
} from './helpers';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('个人信息页面', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('完整流程：直接访问 → Topbar 按钮访问', async ({ page }) => {
    await loginAs(page);
    await thinkDelay(page);

    await page.goto('/profile');
    await thinkDelay(page);
    await expect(page.locator('.topbar__title')).toContainText('个人信息', { timeout: 10000 });
    await expect(page.locator('.sidebar')).toBeVisible();

    const profileButton = page.getByRole('button', { name: '个人信息' });
    if (await profileButton.isVisible()) {
      await humanDelay(page);
      await profileButton.click();
      await thinkDelay(page);
      await expect(page).toHaveURL(/.*profile/);
    }
  });
});
