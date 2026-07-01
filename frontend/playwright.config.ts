import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,        // 调试时串行执行，不弹多个窗口
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,                   // 单 worker，一次只跑一个测试
  timeout: 30000,               // 每个测试 30s 超时（含真实 API 调用）
  reporter: [
    ['html'],
    ['list'],
  ],
  use: {
    // 前端 dev server 地址
    baseURL: process.env.BASE_URL || 'http://localhost:5173',
    // 后端 API 地址（由前端 .env 中的 VITE_API_BASE_URL 决定）
    // 测试前请确保后端服务已启动
    headless: true,           // 无头模式运行，不显示浏览器窗口
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // 启动前端 dev server
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    cwd: '.',
  },
});
