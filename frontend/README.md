# DML V4 Frontend

DML V4 前端，基于 React 19 + TypeScript + Vite。

## 技术栈

- React 19
- TypeScript
- Vite
- ESLint (flat config)

## 目录结构

```text
src/
├── components/          # UI 组件（页面级 + 共享组件）
│   ├── ui/              # 通用 UI 组件（PageHero 等）
│   ├── AppShell.tsx      # 应用主框架（sidebar + topbar）
│   ├── Topbar.tsx        # 顶部导航栏
│   ├── Sidebar.tsx       # 侧边导航栏
│   ├── SearchResultsPage.tsx  # (已废弃，由 pages/SearchPage 替代)
│   ├── GlobalSearch.tsx       # (已废弃)
│   └── ...              # 各功能模块组件
├── pages/               # 独立页面组件
│   └── SearchPage/      # 全局搜索页面
├── services/            # API 客户端（api.ts）
├── providers/           # 全局状态提供者
│   ├── AuthProvider.tsx  # 认证状态
│   └── NavigationProvider.tsx # 导航状态
├── config/              # 配置（导航菜单）
├── types/               # TypeScript 类型定义
├── hooks/               # React hooks
└── constants/           # 常量定义
```

## 页面列表

| 路由 | 对应组件 | 说明 |
|------|----------|------|
| `myTasks` | MyTasksPage | 我的任务 |
| `dashboard` | DashboardPage | 数据统计 |
| `requirements` | RequirementsPage | 测试需求 |
| `testCases` | TestCaseBoardPage | 用例看板 |
| `collections` | TestCaseCollectionPage | 预制用例集 |
| `search` | SearchPage | 全局搜索（独立页面） |
| `agents` | AgentList | 执行代理 |
| `tasks` | TaskList | 执行任务 |
| `testPlanStudioDemo` | TestExecutionPlanDemo | 执行计划 |
| `systemConfig` | SystemConfigPage | 系统配置 |
| `users` | UserManagement | 用户管理 |
| `roles` | RoleManagement | 角色管理 |
| `roleGroup` | RoleGroupManagement | 用户组 |
| `permissions` | PermissionManagement | 权限管理 |
| `catalogLabs` | CatalogLabsPage | Lab 管理 |
| `lineageView` | LineageViewPage | 测试血缘 |

## 样式

- CSS 变量体系在 `index.css` 定义（token 覆盖、主题色、间距、圆角等）
- 组件级样式使用行内 `React.CSSProperties` 对象
- 按钮使用 CSS class：`btn btn--primary`、`btn btn--ghost` 等

## 开发

```bash
npm install
npm run dev      # 开发模式
npm run build    # 构建
npm run lint     # 代码检查
```

## 后端 API

API 客户端位于 `src/services/api.ts`，通过 `VITE_API_BASE_URL` 环境变量配置后端地址。
