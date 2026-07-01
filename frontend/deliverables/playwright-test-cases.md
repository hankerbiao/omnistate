# Playwright E2E 测试用例清单

> **项目**: dmlv4/frontend | **框架**: Playwright | **运行模式**: 无头(headless)
> **最后更新**: 2026-07-01 | **总用例数**: 19 | **通过率**: —
> **后端**: 真实接口（需启动后端服务）

---

## 目录结构

```
e2e/
├── helpers.ts                 # 辅助函数（Mock工厂、认证辅助、人工延迟、关闭等待）
├── login.spec.ts              # 登录认证核心用例（4个）
├── auth-flow.spec.ts          # 保护路由（1个）
├── navigation.spec.ts         # 侧边栏导航（2个）
├── dashboard.spec.ts          # 数据统计页面（2个）
├── theming.spec.ts            # 主题切换（1个）
├── user-switch.spec.ts        # 用户切换（1个）
├── my-tasks.spec.ts           # 我的任务页面（2个）
├── execution-plans.spec.ts    # 执行计划页面（2个）
├── profile.spec.ts            # 个人信息页面（1个）
├── management-pages.spec.ts   # 系统管理页面（2个）
└── requirements.spec.ts       # 创建测试需求完整流程（1个）
```

---

## 设计原则

### 1. 同类别用例共享登录，多步骤连续执行
每个 `test()` 内只登录一次，随后连续执行多个操作步骤，避免每步都重新登录。

### 2. 登录相关用例精简到 4 个
只保留核心场景：页面加载检查、成功登录+写Token+退出、失败提示、Token持久化。

### 3. 人工行为模拟
- `humanDelay()` — 150~350ms 随机间隔，模拟表单填写、按钮点击间的思考时间
- `thinkDelay()` — 400~700ms 随机间隔，模拟页面切换/操作前后的停顿
- `closeDelay()` — 每个用例执行完毕后等待 1 秒再关闭页面

### 4. 全部使用真实后端接口
所有 API 调用直接请求真实后端服务，不拦截不 mock，前后端一体化验证。

> **前置条件**：运行测试前需确保后端服务已启动（`http://localhost:8000`）。

---

## 测试用例详情

### 1. login.spec.ts — 登录认证核心用例（4个）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 1.1 | 登录页加载与默认值 | 访问 `/` → 检查品牌 → 检查表单默认值 → 检查保存密码复选框 | h1: TestHub, 测试管理平台可见, #user_id 默认 admin, #password 默认 Test@123, 复选框未勾选 |
| 1.2 | 成功登录 → 跳转 → 写Token → 退出 | Mock API → 填写凭据 → 点击登录 → 验证跳转 → 验证Token → 退出 → 验证清空 | URL 含 /dashboard, topbar/sidebar 可见, localStorage jwt_token 含 mock-jwt-token, 退出后 token 为 null |
| 1.3 | 凭据错误提示 | Mock 401 → 填写错误凭据 → 点击登录 → 验证错误消息 | 错误消息"登录失败，请检查用户名和密码"可见 |
| 1.4 | Token 持久化与过期 | 注入合法 Token → 刷新保持登录 → 注入过期 Token → 刷新回退登录页 | 合法时 topbar 可见, 过期时 #user_id 可见 |

### 2. auth-flow.spec.ts — 保护路由（1个）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 2.1 | 无Token访问受保护路由 | 直接访问 `/my-tasks`（未登录） | 显示登录页（#user_id 可见, h1: TestHub） |

### 3. navigation.spec.ts — 侧边栏导航（2个）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 3.1 | 管理员完整导航流程 | 登录 → 验证品牌 → 验证4分区 → 依次导航4个页面 | 品牌信息可见, 概览/测试资产/执行/系统分区可见, 页面跳转后标题和URL正确, 高亮切换正确 |
| 3.2 | 受限角色导航项 | 以tester权限登录 → 校验可见/不可见项 | 用例看板可见, 系统配置/数据统计/用户管理不可见 |

### 4. dashboard.spec.ts — 数据统计页面（2个）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 4.1 | 管理员访问仪表盘 | 登录 → 自动跳转 /dashboard | 标题"数据统计", 描述"测试数据整体概览", 侧边栏高亮 |
| 4.2 | 无权限不可见 | 以无 dashboard 权限登录 → 检查导航项 | 数据统计导航项不可见 |

### 5. theming.spec.ts — 主题切换（1个）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 5.1 | 完整主题流程 | 登录 → 检查按钮 → 切换主题 → 刷新检查持久化 | 按钮可见, 主题值改变, 刷新后保持一致 |

### 6. user-switch.spec.ts — 用户切换（1个）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 6.1 | 完整切换流程 | 以admin登录 → 验证6个用户chip → 验证高亮禁用 → 切换到tester → 验证权限更新 | 6 个用户chip可见, 管理员高亮禁用, 切换后系统配置不可见, 新用户chip高亮 |

### 7. my-tasks.spec.ts — 我的任务页面（2个）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 7.1 | 导航与直接访问 | 登录 → 侧边栏导航 → URL直接访问 | 标题"我的任务", URL含 /my-tasks, 侧边栏高亮 |
| 7.2 | 默认跳转 | 以无dashboard权限登录 | 自动跳转 /my-tasks, 标题"我的任务" |

### 8. execution-plans.spec.ts — 执行计划页面（2个）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 8.1 | 有权限导航 | 登录 → 点击执行计划 | 标题"执行计划", URL含 /execution-plans, 侧边栏高亮 |
| 8.2 | 无权限不可见 | 以无权限登录 → 检查导航项 | 执行计划导航项不可见 |

### 9. profile.spec.ts — 个人信息页面（1个）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 9.1 | 直接访问与Topbar入口 | 登录 → URL访问 /profile → Topbar按钮访问 | 标题"个人信息", sidebar可见, URL含 /profile |

### 10. management-pages.spec.ts — 系统管理页面（2个）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 10.1 | 连续导航4个管理页面 | 登录 → 用户管理 → 角色管理 → 权限管理 → 滚动 → 系统配置 | 每个页面标题和URL正确 |
| 10.2 | 权限控制 | 以无 roles:read 权限登录 | 角色管理/用户组管理不可见, 用户管理可见 |

### 11. requirements.spec.ts — 创建测试需求完整流程（1个，AI驱动）

| # | 用例名称 | 步骤 | 验证点 |
|---|---------|------|--------|
| 11.1 | AI生成数据 → 打开新建表单 → 填写全部字段 → 提交创建 → 验证成功 | 调用AI(seedcoder)生成需求数据 → 登录 → 导航到需求页 → 点"+ 新建" → AI数据填入标题/优先级/分类/验收标准 → 填写起止日期 → AI推荐标签作为自定义标签输入 → AI生成的4个结构化描述填入 → 提交 → 验证成功消息 → 关闭 | 模态框弹出, 创建中按钮可见, 成功消息"需求已创建", AI生成用例和完成按钮可见, 关闭后模态框消失 |

---

## AI 辅助

测试套件包含一个 `e2e/ai-helper.ts` 工具模块，用于调用内部 LLM 服务（`seedcoder`）生成测试数据。

**API 地址**: `http://10.8.136.35:8881/v1/chat/completions`

**当前用途**：`requirements.spec.ts` 中的创建需求测试，所有表单内容（标题、描述、标签、验收标准等）由 AI 动态生成，每次运行数据不同，覆盖更多场景变体。

**可扩展方向**：
1. 其他表单填充场景（创建用户、创建用例等）
2. AI 视觉回归（截图对比）
3. AI 失败分析（截图+DOM→原因推测→修复建议）

---

## 运行方法

> ⚠️ 测试依赖真实后端接口，运行前请确保后端服务已启动（默认 `http://localhost:8000`）。
> 前端 dev server 由 Playwright 自动启动（配置在 `playwright.config.ts` 的 `webServer` 中）。

```bash
# 全部运行（无头模式）
npx playwright test

# 运行单个文件
npx playwright test e2e/login.spec.ts

# 有头模式（观察浏览器执行过程）
npx playwright test --headed

# 查看 HTML 报告
npx playwright show-report
```

---

## 维护指南

### 新增用例规范

```typescript
import { test, expect } from '@playwright/test';
import { mockAuthApis, adminPermissions, DEFAULT_USER_ID, DEFAULT_PASSWORD, humanDelay, thinkDelay, closeDelay } from './helpers';

test.afterEach(async ({ page }, testInfo) => {
  await closeDelay(page, testInfo);
});

test.describe('页面名称', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('完整流程描述', async ({ page }) => {
    // 1. 登录（一次）
    await mockAuthApis(page, DEFAULT_USER_ID, adminPermissions());
    await page.goto('/');
    await humanDelay(page);
    await page.locator('#user_id').fill(DEFAULT_USER_ID);
    await humanDelay(page);
    await page.locator('#password').fill(DEFAULT_PASSWORD);
    await thinkDelay(page);
    await page.getByRole('button', { name: /^登录$/ }).click();
    await expect(page).toHaveURL(/.*dashboard/, { timeout: 10000 });
    await thinkDelay(page);

    // 2. 执行多个操作步骤...
    // 3. 验证结果...
  });
});
```

### 更新此文档
每次新增/修改/删除测试用例后，同步更新本文件：
1. 更新测试总数
2. 更新/追加用例表格
3. 更新最后更新日期
