# 前端控制台

`frontend/` 是开放平台控制台，负责展示网关能力并提供管理入口。

## 启动命令

```bash
cd frontend
npm install
npm run dev
```

构建：

```bash
npm run build
```

测试：

```bash
npm run test:run
```

## 目录结构

```text
frontend/src/
├── components/             # Layout、通用 UI、图标
├── config/                 # Scope 配置
├── mock/                   # Mock 数据与处理器
├── pages/                  # 页面组件
├── services/               # API 客户端
├── styles/                 # 主题样式
├── types.ts                # 领域类型
└── utils.ts
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_OPEN_PLATFORM_API_BASE_URL` | `http://127.0.0.1:8820` | 网关地址 |
| `VITE_OPEN_PLATFORM_CONSOLE_TOKEN` | `dev-console-token` | 控制台 Token |
| `VITE_OPEN_PLATFORM_USE_MOCK` | `false` | 是否启用 Mock |

## API 客户端行为

`src/services/api.ts` 会将控制台路径拼接为：

```text
${VITE_OPEN_PLATFORM_API_BASE_URL}/api/v1/open-platform${path}
```

如果启用 Mock，会动态加载 `src/mock/handlers.ts`，避免生产构建包含不必要的 Mock 分支。

## 页面职责

| 页面文件 | 职责 |
| --- | --- |
| `Overview.tsx` | 展示调用统计和趋势 |
| `ApiKeys.tsx` | 密钥创建、撤销、删除 |
| `Capabilities.tsx` | 能力目录和 Scope |
| `ApiDebugger.tsx` | 能力探测与响应查看 |
| `Logs.tsx` | 调用日志 |
| `UserPermissions.tsx` | 用户能力授权 |
| `UserQuota.tsx` | 用户配额设置 |
| `Mcp.tsx` | MCP 接入说明 |

## 开发注意事项

- 前端默认不静默回退 Mock，网关不可用时会抛出错误，便于尽早发现联调问题。
- API 类型集中在 `src/types.ts`，新增接口时优先补齐类型。
- 高风险操作需要在 UI 中提供清晰状态，例如撤销密钥、删除密钥、修改权限。
