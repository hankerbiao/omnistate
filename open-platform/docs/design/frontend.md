# 前端设计

开放平台前端是面向管理和调试的控制台，不是营销页面。设计目标是让管理员和开发者高效完成 API 治理任务。

## 技术栈

| 技术 | 用途 |
| --- | --- |
| React 19 | UI 渲染 |
| TypeScript | 类型约束 |
| Vite | 开发服务器与构建 |
| Vitest | 单元测试 |
| ESLint + Prettier | 代码质量与格式化 |

## 页面结构

| 页面 | 说明 |
| --- | --- |
| Overview | 平台调用概览 |
| ApiKeys | API Key 管理 |
| Capabilities | 开放能力目录 |
| ApiDebugger | 在线调试 |
| Logs | 调用日志 |
| UserPermissions | 用户能力授权 |
| UserQuota | 用户配额 |
| Mcp | MCP 接入说明 |
| Login | 登录页 |

## 数据访问

前端 API 客户端位于 `src/services/api.ts`。默认请求：

```text
http://127.0.0.1:8820/api/v1/open-platform
```

请求头：

```text
Content-Type: application/json
X-Console-Token: dev-console-token
X-Console-User-Id: user_admin
```

只有显式设置 `VITE_OPEN_PLATFORM_USE_MOCK=true` 时才使用 Mock。

## 视觉系统

当前设计语言参考 `frontend/DESIGN.md` 中的 Supabaze 风格分析：

- 白色或近白色画布
- 近黑色文字
- 绿色作为主要行动色
- 紧凑、技术感强的卡片和表格
- 以实际产品 UI 和数据为主要信息载体

## 交互原则

- 对密钥、权限、配额等高风险操作提供明确状态反馈。
- 调试台展示请求 URL、状态码、耗时和响应体，便于定位问题。
- 能力目录展示 Scope 和参数，让开发者在同一页面完成理解与试调。
- 调用日志保留请求 ID 和诊断信息，服务于真实排障。
