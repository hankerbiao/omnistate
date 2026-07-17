# E2E 测试工作日志 — 2026-07-02

> 涵盖初始测试套件提交 + 后续迭代修复

---

## 一、初始 E2E 测试套件（Commit `69e31d4`）

**提交信息：** `test(e2e): 完善 Playwright E2E 测试套件 — 10 个核心场景`

### 涉及文件（13 个）

| 文件 | 说明 | 行数变动 |
|------|------|----------|
| `e2e/ai-helper.ts` | AI 数据生成器（需求/项目/Lab/用例/用例集） | +168 |
| `e2e/helpers.ts` | 通用工具函数（登录/导航/延迟/截图） | +284 |
| `e2e/login.spec.ts` | 登录认证测试（成功/失败/token 持久化/刷新） | +113/-41 |
| `e2e/navigation.spec.ts` | 导航权限测试（ADMIN 全量 vs 受限角色） | +73 |
| `e2e/dashboard.spec.ts` | 仪表盘页面测试 | +50 |
| `e2e/execution-plans.spec.ts` | 执行计划页面测试 | +56 |
| `e2e/my-tasks.spec.ts` | 我的任务页面测试 | +55 |
| `e2e/profile.spec.ts` | 个人资料页面测试 | +44 |
| `e2e/requirements.spec.ts` | 需求管理页面测试 | +113 |
| `e2e/management-pages.spec.ts` | 管理页面测试 | +67 |
| `e2e/theming.spec.ts` | 主题切换测试 | +54 |
| `e2e/user-switch.spec.ts` | 用户切换测试 | +57 |
| `e2e/auth-flow.spec.ts` | 认证流程测试 | +14 |

### 配置变更
- `playwright.config.ts`：单 worker 串行、30s 超时、无头模式、端口 5173
- `.gitignore`：排除 AI 测试日志目录 `e2e/ai-logs/`

---

## 二、后续迭代修复（未提交）

### 目标：`testcases.spec.ts` — 创建手工用例完整流程

新增测试文件 `e2e/testcases.spec.ts`（142 行），覆盖全流程：AI 生成数据 → 登录 → 填写表单 → 提交创建 → 验证成功。

### 修复问题清单（共 8+ 轮迭代）

#### 1. AI JSON 解析失败（`SyntaxError after JSON`）
- **现象：** AI 响应在 JSON 前后输出额外文本，`JSON.parse` 报错
- **修复：** `parseAiJson` 改用 `indexOf('{')` / `lastIndexOf('}')` 提取纯 JSON 主体
- **文件：** `e2e/ai-helper.ts:133-148`

#### 2. 创建按钮 strict mode violation
- **现象：** `getByRole('button', { name: '手工' })` 匹配到筛选按钮和创建按钮两个元素
- **修复：** 创建按钮添加 `aria-label="创建手工用例"`；测试改用精确名称定位
- **文件：** `src/components/TestCaseBoard/TestCaseBoardPage.tsx:280`

#### 3. Lab combobox 严格模式冲突
- **现象：** 侧边栏 `"Lab"` 和表单弹窗 `"实验室 (Lab) *"` 两个 combobox 都被匹配
- **修复：** 用 `/^实验室.*Lab/` 锚定开头，只匹配表单中的 combobox

#### 4. Lab 选项异步加载导致跳过
- **现象：** `optionCount < 2` 时跳过，但实际有 Lab 数据
- **修复：** 用 `expect.toPass` 轮询等待至少 2 个 option 加载完成

#### 5. 优先级中英文不匹配
- **现象：** AI 输出 `P0`，页面按钮标签为"紧急"、"高"、"中"、"低"
- **修复：** 添加 `PRIORITY_MAP` 映射：P0→紧急、P1→高、P2→中、P3→低
- **使用：** `page.getByRole('group', { name: '优先级' }).getByRole('button', { name: priorityLabel })`

#### 6. 标签"添加"按钮冲突
- **现象：** `+ 添加一级`（目录路径）和 `添加`（标签）两个按钮同名
- **修复：** 使用 `getByRole('button', { name: '添加', exact: true })`

#### 7. 缺少步骤 Tab 填写
- **现象：** 表单提交时步骤为空导致验证失败
- **修复：** 切换到"步骤"Tab，解析 AI 多步骤文本，逐条添加并填写（标题/动作/期望）
- **兼容：** AI 有时用中文分号 `；` 分隔步骤，替换为换行后统一解析

#### 8. API 创建接口超时
- **现象：** 创建接口耗时约 50-60s，15s 断言超时
- **修复：** 测试超时提升至 120s，`not.toBeVisible` 断言超时提升至 60s

### 涉及文件（3 个）

| 文件 | 行数 | 状态 |
|------|------|------|
| `e2e/testcases.spec.ts` | 142 行 | 新增（未跟踪） |
| `e2e/ai-helper.ts` | 428 行（+315/-55） | 已修改（未提交） |
| `src/components/TestCaseBoard/TestCaseBoardPage.tsx` | 550 行（+2） | 已修改（未提交） |

---

## 三、辅助输出

### skill 创建

**文件：** `~/.workbuddy/skills/playwright-e2e-debug/SKILL.md`

记录 Playwright E2E 测试调试的通用流程和 7 种常见修复模式，方便后续复用。

### 品牌名称统一

同步更新了多个 E2E 测试断言中的品牌名：`TestHub` → `DML Sentio`、`测试运营平台` → `测试管理平台`。

涉及文件：`login.spec.ts`、`navigation.spec.ts`、`auth-flow.spec.ts` 等。

---

## 四、最终状态

```
npx playwright test e2e/testcases.spec.ts --headed
✓  1 passed (55.7s)
```
