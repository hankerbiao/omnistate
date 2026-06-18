# 前端 UI 代码评审与优化方案

> 评审范围：DML V4 前端（`frontend/src/`）
> 评审日期：2026-06-18
> 评审人：CodeBuddy Code
> 目标受众：前端开发团队（按此方案执行修复）

---

## 一、问题总览

| 优先级 | 问题数量 | 影响范围 |
|--------|----------|----------|
| **P0**（必须立即修复） | 2 | 可维护性、类型安全 |
| **P1**（本周内修复） | 4 | 代码复用、开发效率 |
| **P2**（近期规划） | 3 | 架构统一、技术债务 |
| **P3**（细节优化） | 2 | 用户体验、组件完善 |

---

## 二、P0 级问题（必须立即修复）

### 2.1 `TestExecutionPlanDemo.tsx` 单文件爆炸（2607 行）

**位置**：`frontend/src/components/TestExecutionPlanDemo.tsx`

**问题描述**：
一个文件里包含 14 个组件/逻辑单元，数据获取、业务逻辑、状态管理、UI 渲染全部耦合。导致无法单元测试、代码审查困难、多人协作冲突率高。

**当前结构**：
```
TestExecutionPlanDemo.tsx (2607 行)
├── TestExecutionPlanDemo (主组件，18 个 useState)
├── PlanSidebar
├── PlanDetailView
├── StatusBoard
├── StatusCard
├── ComponentBoard
├── DataTable
├── AddCasesModal
├── CreatePlanWizard
├── DateRangePicker
├── ArchivedModal
├── OverviewView
├── ResultModal
└── RerunConfirmModal
```

**优化方案：拆分为独立模块**

```
frontend/src/components/execution-plan/
├── index.tsx                 # 主页面，保留路由入口和状态编排
├── PlanSidebar.tsx           # 左侧计划列表
├── PlanDetailView.tsx        # 右侧详情容器
├── StatusBoard.tsx           # 状态看板（待执行/执行中/失败/已完成）
├── StatusCard.tsx            # 状态卡片
├── ComponentBoard.tsx        # 组件视图
├── DataTable.tsx             # 数据表格（列表视图）
├── AddCasesModal.tsx         # 添加用例弹窗
├── CreatePlanWizard.tsx      # 创建计划向导（多步骤表单）
├── DateRangePicker.tsx       # 日期范围选择器（如其他地方不用，可保留内联）
├── ArchivedModal.tsx         # 归档弹窗
├── OverviewView.tsx          # 概览视图
├── ResultModal.tsx           # 执行结果弹窗
├── RerunConfirmModal.tsx     # 重跑确认弹窗
└── types.ts                  # 提取 PlanSummary、PlanItemSummary 等本地类型
```

**迁移步骤**：
1. 先提取 `types.ts`，把第 30-60 行的本地 interface 移过去
2. 逐个提取子组件，从底部开始（先 `RerunConfirmModal`，再 `ResultModal`……）
3. 每一步提取后运行 `npm run lint` 确保类型无报错
4. 最后提取主组件中的数据获取逻辑到 `hooks/useExecutionPlan.ts`

**状态管理拆分建议**：
```typescript
// hooks/useExecutionPlan.ts
export function useExecutionPlan() {
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // ... 把主组件中 93-125 行的状态管理移到这里
}
```

---

### 2.2 `types/index.ts` 存在重复的类型定义

**位置**：`frontend/src/types/index.ts:955-1002` 和 `frontend/src/types/index.ts:1206-1253`

**问题描述**：
同一组 Collection 接口定义了两遍，字段差异极小（`description` 的 `?` 可选修饰符不一致）。这会导致 TypeScript 在某些场景下产生兼容性错误，且维护时极易改一处漏一处。

**重复定义清单**：
| 接口名 | 第 1 处 | 第 2 处 | 差异 |
|--------|---------|---------|------|
| `CollectionListItem` | 955 | 1206 | `description?: string \| null` vs `description: string \| null` |
| `CollectionResponse` | 966 | 1217 | 同上 |
| `CreateCollectionRequest` | 980 | 1231 | `description?: string` vs `description?: string \| null` |
| `UpdateCollectionRequest` | 988 | 1239 | `description?: string` vs `description?: string \| null` |
| `AddCasesRequest` | 994 | 1245 | 无差异 |
| `RemoveCasesRequest` | 999 | 1250 | 无差异 |

**优化方案**：
1. 删除第 1206-1253 行的重复定义（保留第 955-1002 行的版本）
2. 统一 `description` 为 `description?: string | null`（最宽松的定义，兼容两边）
3. 搜索全项目确认这些接口的使用点，修复可能的类型报错

```typescript
// 保留并优化后的定义（约 955 行）
export interface CollectionListItem {
  collection_id: string;
  name: string;
  description?: string | null;
  tags: string[];
  case_count: number;
  auto_case_count: number;
  created_by: string;
  updated_at: string;
}

export interface CollectionResponse {
  collection_id: string;
  name: string;
  description?: string | null;
  tags: string[];
  case_ids: string[];
  auto_case_ids: string[];
  case_count: number;
  auto_case_count: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CreateCollectionRequest {
  name: string;
  description?: string | null;
  tags?: string[];
  case_ids?: string[];
  auto_case_ids?: string[];
}

export interface UpdateCollectionRequest {
  name?: string;
  description?: string | null;
  tags?: string[];
}

export interface AddCasesRequest {
  case_ids?: string[];
  auto_case_ids?: string[];
}

export interface RemoveCasesRequest {
  case_ids?: string[];
  auto_case_ids?: string[];
}
```

---

## 三、P1 级问题（本周内修复）

### 3.1 提取通用 `Modal` 组件（15+ 处重复）

**影响文件**：
- `TestExecutionPlanDemo.tsx`（ResultModal、ArchivedModal、RerunConfirmModal、AddCasesModal、CreatePlanWizard）
- `ProfilePage.tsx`（权限弹窗）
- `PermissionManagement.tsx`（多个弹窗）
- `LinkManualCaseModal.tsx`（整个文件就是弹窗）
- `ReassignModal.tsx`（整个文件就是弹窗）
- `ExecRecordsModal.tsx`
- `ExecResultModal.tsx`
- `CaseGovernancePage.tsx`
- `SingleDispatchModal.tsx`
- `ResultBackfillModal.tsx`
- `ProjectsPage.tsx`
- `TestCaseBoardExplorer.tsx`

**重复代码模式**：
```tsx
<div style={{
  position: 'fixed', inset: 0,
  background: 'rgba(0,0,0,0.4)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 1000
}}>
  <div style={{
    background: 'var(--surface-primary)', borderRadius: 12,
    width: 500, maxWidth: '90vw', boxShadow: '0 8px 32px rgba(0,0,0,0.3)'
  }}>
    {/* header + body + footer */}
  </div>
</div>
```

**优化方案：创建 `Modal` 组件**

```tsx
// components/ui/Modal.tsx
import { useCallback, useEffect } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  width?: number | string;
  maxWidth?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  closeOnOverlayClick?: boolean;
}

export default function Modal({
  open, onClose, title, width = 500, maxWidth = '90vw',
  children, footer, closeOnOverlayClick = true
}: ModalProps) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed', inset: 0,
        background: 'var(--overlay-bg)', backdropFilter: 'blur(2px)',
        zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={() => closeOnOverlayClick && onClose()}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--surface-primary)', borderRadius: 12,
          width, maxWidth, maxHeight: '85vh', display: 'flex', flexDirection: 'column',
          boxShadow: '0 25px 80px rgba(0,0,0,0.3)', border: '1px solid var(--border-default)',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '14px 20px', borderBottom: '1px solid var(--border-subtle)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>{title}</span>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18, color: 'var(--text-tertiary)' }}
            aria-label="关闭"
          >×</button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
```

**使用示例**：
```tsx
// 替换 ProfilePage 的权限弹窗
<Modal
  open={permModalOpen}
  onClose={() => setPermModalOpen(false)}
  title="权限详情"
  width={600}
>
  {/* 权限列表内容 */}
</Modal>

// 替换 ResultModal
<Modal
  open={showResult}
  onClose={onClose}
  title="执行结果"
  width={680}
>
  <TimelineView items={...} />
</Modal>
```

**实施步骤**：
1. 创建 `components/ui/Modal.tsx`
2. 在 `ProfilePage.tsx` 中试用，验证效果
3. 逐个替换其他文件中的内联弹窗（从最简单的开始）
4. 删除旧的内联弹窗代码

---

### 3.2 提取通用 `Card` / `LoadingSpinner` / `ErrorBanner` 组件

**影响文件**：几乎所有页面组件（`ProfilePage.tsx`、`RequirementsPage.tsx`、`AppShell.tsx`、`UserManagement.tsx`、`LoginPage.tsx` 等）

**重复的样式定义**（每个文件底部都有类似的 `styles` 对象）：
```tsx
const styles = {
  container: { padding: '32px', maxWidth: '1000px', margin: '0 auto' },
  card: { backgroundColor: 'var(--surface-primary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)' },
  cardHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)' },
  cardBody: { padding: '20px' },
  loadingState: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', padding: '40px', color: 'var(--text-tertiary)' },
  spinner: { width: '20px', height: '20px', border: '2px solid var(--border-default)', borderTopColor: 'var(--accent-primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' },
  errorBanner: { padding: '12px 16px', borderRadius: 'var(--radius-md)', background: 'var(--status-error-bg)', color: 'var(--status-error)', display: 'flex', alignItems: 'center', gap: '8px' },
  badge: { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minWidth: '24px', height: '24px', padding: '0 8px', fontSize: '12px', fontWeight: 600, color: 'var(--accent-primary)', backgroundColor: 'var(--status-info-bg)', borderRadius: '12px' },
};
```

**优化方案：创建 `components/ui/` 通用组件**

```tsx
// components/ui/Card.tsx
interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card = ({ children, className }: CardProps) => (
  <div className={`bg-[var(--surface-primary)] border border-[var(--border-subtle)] rounded-[var(--radius-lg)] overflow-hidden ${className || ''}`}>
    {children}
  </div>
);

export const CardHeader = ({ children }: { children: React.ReactNode }) => (
  <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border-subtle)] bg-[var(--surface-secondary)]">
    {children}
  </div>
);

export const CardBody = ({ children }: { children: React.ReactNode }) => (
  <div className="p-5">{children}</div>
);

export const CardTitle = ({ children }: { children: React.ReactNode }) => (
  <h2 className="text-[15px] font-semibold text-[var(--text-primary)] m-0">{children}</h2>
);
```

```tsx
// components/ui/LoadingSpinner.tsx
export const LoadingSpinner = ({ text = '加载中...' }: { text?: string }) => (
  <div className="flex items-center justify-center gap-3 py-10 text-[var(--text-tertiary)]">
    <div className="w-5 h-5 border-2 border-[var(--border-default)] border-t-[var(--accent-primary)] rounded-full animate-spin" />
    <span>{text}</span>
  </div>
);
```

```tsx
// components/ui/ErrorBanner.tsx
export const ErrorBanner = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <div className="flex items-center gap-2 px-4 py-3 rounded-[var(--radius-md)] bg-[var(--status-error-bg)] text-[var(--status-error)]">
    <span>⚠</span>
    <span>{message}</span>
    {onRetry && (
      <button onClick={onRetry} className="ml-auto btn btn--sm btn--ghost">重试</button>
    )}
  </div>
);
```

**实施步骤**：
1. 创建上述 3 个 UI 组件
2. 在 `ProfilePage.tsx` 中试用，替换 `styles` 对象中的相关定义
3. 逐步推广到 `RequirementsPage.tsx`、`UserManagement.tsx` 等文件
4. 每页替换后删除对应的 `styles` 条目

---

### 3.3 用 Tailwind CSS 替代内联 `style={{ }}`

**项目状态**：已配置 TailwindCSS v4（`frontend/package.json` 确认），但代码中几乎没有使用 Tailwind 类名，90% 样式是内联 `style` 对象。

**示例：ProfilePage 的 InfoGrid 重构**

```tsx
// 修改前（ProfilePage.tsx ~290 行）
<div style={styles.infoGrid}>
  <div style={styles.infoItem}>
    <span style={styles.infoLabel}>用户ID</span>
    <span style={styles.infoValue} className="mono">{userInfo.user_id}</span>
  </div>
  ...
</div>

// 修改后
<div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4">
  <div className="flex flex-col gap-1">
    <span className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">用户ID</span>
    <span className="text-sm text-[var(--text-primary)] font-mono">{userInfo.user_id}</span>
  </div>
  ...
</div>
```

**实施策略**：
1. 不要一次性全改，选择 1-2 个页面做试点（建议从 `ProfilePage.tsx` 开始，因为它相对较小且结构清晰）
2. 将常用样式组合提取为 Tailwind 组件类（在 `index.css` 或专门的组件文件里用 `@layer components`）
3. 删除 `styles` 对象后确认无视觉回归

---

### 3.4 统一状态颜色常量（Design Token）

**影响文件**：
- `TestExecutionPlanDemo.tsx:71-76`（`STATUS_META`）
- `ProfilePage.tsx:158-165`（`getStatusStyle`）
- `RequirementsPage.tsx:27-34`（`CATEGORY_COLORS`）
- `TestExecutionPlanDemo.tsx:1139-1197`（`StatusCard` 内联颜色）

**优化方案：创建 `theme.ts`**

```typescript
// src/theme.ts
export const STATUS_COLORS = {
  success:   { color: '#3fb950', bg: 'rgba(63,185,80,0.08)',  border: 'rgba(63,185,80,0.3)'  },
  error:     { color: '#f85149', bg: 'rgba(248,81,73,0.08)',   border: 'rgba(248,81,73,0.3)'  },
  warning:   { color: '#d29922', bg: 'rgba(210,153,34,0.08)', border: 'rgba(210,153,34,0.3)' },
  info:      { color: '#58a6ff', bg: 'rgba(88,166,255,0.08)',  border: 'rgba(88,166,255,0.3)' },
  neutral:   { color: '#8b949e', bg: 'rgba(139,148,158,0.08)', border: 'rgba(139,148,158,0.3)' },
} as const;

export const PRIORITY_COLORS = {
  P0: '#f85149',
  P1: '#d29922',
  P2: '#58a6ff',
  P3: '#8b949e',
} as const;

export const PLAN_STATUS_COLORS = {
  active:   { color: '#3fb950', label: '进行中' },
  done:     { color: '#8b949e', label: '已完成' },
} as const;

// 用例执行状态映射
export const ITEM_STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: '待执行', color: STATUS_COLORS.neutral.color, bg: STATUS_COLORS.neutral.bg },
  running: { label: '执行中', color: STATUS_COLORS.info.color, bg: STATUS_COLORS.info.bg },
  fail:    { label: '失败',   color: STATUS_COLORS.error.color, bg: STATUS_COLORS.error.bg },
  done:    { label: '已完成', color: STATUS_COLORS.success.color, bg: STATUS_COLORS.success.bg },
};

// 用户状态映射
export const USER_STATUS_COLORS: Record<string, { color: string; bg: string }> = {
  ACTIVE:   { color: STATUS_COLORS.success.color, bg: 'var(--status-success-bg)' },
  INACTIVE: { color: 'var(--text-tertiary)', bg: 'var(--surface-tertiary)' },
  PENDING:  { color: STATUS_COLORS.warning.color, bg: 'var(--status-warning-bg)' },
};
```

**替换示例**：
```tsx
// 修改前（TestExecutionPlanDemo.tsx）
const STATUS_META = {
  pending: { label: '待执行', color: '#8b949e', bg: 'rgba(139,148,158,0.08)' },
  running: { label: '执行中', color: '#58a6ff', bg: 'rgba(88,166,255,0.08)' },
  fail:    { label: '失败',   color: '#f85149', bg: 'rgba(248,81,73,0.08)' },
  done:    { label: '已完成', color: '#3fb950', bg: 'rgba(63,185,80,0.08)' },
};

// 修改后
import { ITEM_STATUS_META } from '../theme';
// 直接使用 ITEM_STATUS_META[status]
```

---

## 四、P2 级问题（近期规划）

### 4.1 统一使用 TanStack Query 替代手动 `useState` + `useEffect` 请求

**现状**：
- `UserManagement.tsx` 已使用 `useQuery` / `useMutation`（良好实践）
- `ProfilePage.tsx` 使用 `useState` + `useEffect` + `useCallback` 手动 fetch
- `TestExecutionPlanDemo.tsx` 使用 18 个 `useState` 管理所有状态

**优化方案**：

```tsx
// 修改前（ProfilePage.tsx:54-90）
const fetchUserData = useCallback(async () => {
  setLoading(true);
  setError(null);
  try {
    const [userRes, permsRes] = await Promise.all([
      api.getCurrentUser(),
      api.getCurrentUserPermissions(),
    ]);
    if (userRes.code === 0 || userRes.code === 200) {
      setUserInfo(userRes.data);
    } else {
      setError(userRes.message || '获取用户信息失败');
      return;
    }
    if (permsRes.code === 0 || permsRes.code === 200) {
      setPermissionsInfo(permsRes.data);
    }
    try {
      const allPermsRes = await api.listPermissions();
      if (allPermsRes.code === 0 || allPermsRes.code === 200) {
        setAllPermissions(allPermsRes.data || []);
      }
    } catch { /* 静默降级 */ }
  } catch (err) {
    setError('获取用户信息失败');
  } finally {
    setLoading(false);
  }
}, []);

useEffect(() => { fetchUserData(); }, [fetchUserData]);
```

```tsx
// 修改后
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '../providers/queryKeys';

const { data: userInfo, isLoading: userLoading, error: userError } = useQuery({
  queryKey: queryKeys.users.current,
  queryFn: async () => {
    const res = await api.getCurrentUser();
    if (res.code !== 0 && res.code !== 200) throw new Error(res.message || '获取用户信息失败');
    return res.data;
  },
});

const { data: permissionsInfo } = useQuery({
  queryKey: queryKeys.permissions.current,
  queryFn: async () => {
    const res = await api.getCurrentUserPermissions();
    return res.code === 0 || res.code === 200 ? res.data : null;
  },
});

const { data: allPermissions } = useQuery({
  queryKey: queryKeys.permissions.all,
  queryFn: async () => {
    const res = await api.listPermissions();
    return res.code === 0 || res.code === 200 ? res.data || [] : [];
  },
  // 非管理员会报错，但 useQuery 会自动处理失败，不需要 try/catch
});
```

**实施步骤**：
1. 在 `queryKeys.ts` 中补充缺失的 key 定义
2. 从 `ProfilePage.tsx` 开始试点（数据量小，逻辑简单）
3. 逐步迁移 `RequirementsPage.tsx`、`MyTasksPage.tsx` 等页面
4. 最后迁移 `TestExecutionPlanDemo.tsx`（配合文件拆分一起进行）

---

### 4.2 拆分 API Client 和 Types 为 Domain 模块

**当前问题**：
- `services/api.ts` 第 1 行导入 50+ 个类型，文件内有 100+ 个方法
- `types/index.ts` 1459 行，所有领域模型混在一起

**优化方案**：

```
src/
├── services/
│   ├── api/
│   │   ├── client.ts          # 基础 request / Token 管理
│   │   ├── auth.ts            # login, logout
│   │   ├── users.ts           # listUsers, updateUser, getCurrentUser
│   │   ├── requirements.ts    # createRequirement, listRequirements
│   │   ├── testCases.ts       # listTestCases, updateTestCase
│   │   ├── execution.ts       # dispatchTask, rerunTask, getTaskStatus
│   │   ├── collections.ts     # collection CRUD
│   │   └── index.ts           # 统一导出
│   └── catalogLabsCache.ts
└── types/
    ├── index.ts               # 只保留通用类型（ApiResponse, PaginationParams）
    ├── auth.ts                # LoginRequest, UserResponse, etc.
    ├── requirements.ts        # RequirementResponse, CreateRequirementRequest
    ├── testCases.ts           # TestCaseResponse, TestCaseStep
    ├── execution.ts           # ExecutionTask, PlanTaskItemResponse
    └── collections.ts         # CollectionResponse, CollectionListItem
```

**实施步骤**：
1. 先按 domain 拆分 `types/index.ts`（无业务逻辑，纯移动，风险最低）
2. 修改 `services/api.ts` 的 import 路径
3. 逐步将方法按 domain 提取到新文件
4. 更新所有页面组件的 import 路径（可以用 IDE 的 move 重构自动处理）

---

### 4.3 提取 `useApi` Hook 统一处理 `loading` / `error` / `data`

**当前问题**：21+ 个文件重复声明：
```tsx
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
const [data, setData] = useState<T[]>([]);
```

**优化方案**：

```tsx
// hooks/useApi.ts
import { useState, useCallback } from 'react';

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  execute: (...args: any[]) => Promise<void>;
  reset: () => void;
}

export function useApi<T>(apiFn: (...args: any[]) => Promise<{ code: number; data?: T; message?: string }>): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (...args: any[]) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFn(...args);
      if (res.code === 0 || res.code === 200) {
        setData(res.data ?? null);
      } else {
        setError(res.message || '请求失败');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '请求失败');
    } finally {
      setLoading(false);
    }
  }, [apiFn]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { data, loading, error, execute, reset };
}
```

**使用示例**：
```tsx
// 修改前（ProfilePage）
const [userInfo, setUserInfo] = useState<UserResponse | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
// ... 手动 fetch

// 修改后
const { data: userInfo, loading, error, execute: fetchUser } = useApi(api.getCurrentUser);
useEffect(() => { fetchUser(); }, [fetchUser]);
```

> **注**：如果团队决定全面迁移到 TanStack Query（4.1），此 Hook 可以省去；如果部分页面暂不迁移，此 Hook 可作为过渡方案。

---

## 五、P3 级问题（细节优化）

### 5.1 提取 `InlineEditField` 组件替换复制粘贴的编辑逻辑

**位置**：`frontend/src/components/ProfilePage.tsx:167-241`

**问题**：Email 编辑和 Itcode 编辑的 state + handler 几乎完全复制粘贴。

**优化方案**：

```tsx
// components/ui/InlineEditField.tsx
import { useState, useCallback } from 'react';

interface InlineEditFieldProps {
  label: string;
  value: string | undefined;
  onSave: (value: string) => Promise<void>;
  validator?: (value: string) => string | true; // true 表示通过
  placeholder?: string;
  emptyText?: string;
  successText?: string;
}

export default function InlineEditField({
  label, value, onSave, validator, placeholder, emptyText = '未设置', successText = '已更新',
}: InlineEditFieldProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const startEdit = useCallback(() => {
    setDraft(value || '');
    setEditing(true);
    setError(null);
    setSuccess(null);
  }, [value]);

  const cancelEdit = useCallback(() => {
    setEditing(false);
    setDraft('');
    setError(null);
  }, []);

  const handleSave = useCallback(async () => {
    const trimmed = draft.trim();
    if (validator) {
      const result = validator(trimmed);
      if (result !== true) { setError(result); return; }
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(trimmed);
      setEditing(false);
      setSuccess(successText);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  }, [draft, onSave, validator, successText]);

  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wider">{label}</span>
      <div className="flex items-center gap-2">
        {editing ? (
          <>
            <input
              className="form-input flex-1 text-[13px] min-w-[180px]"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') cancelEdit(); }}
              placeholder={placeholder}
              autoFocus
              disabled={saving}
            />
            <button className="btn btn--primary btn--sm whitespace-nowrap text-xs py-1 px-3" onClick={handleSave} disabled={saving}>
              {saving ? '保存中…' : '保存'}
            </button>
            <button className="btn btn--ghost btn--sm whitespace-nowrap text-xs py-1 px-3" onClick={cancelEdit} disabled={saving}>
              取消
            </button>
          </>
        ) : (
          <>
            <span className="text-sm text-[var(--text-primary)]">
              {value || <span className="text-[var(--text-tertiary)] italic">{emptyText}</span>}
            </span>
            <button className="btn btn--ghost btn--sm text-[11px] px-2 py-0.5 leading-relaxed" onClick={startEdit} title={`编辑${label}`}>
              ✏️ 编辑
            </button>
          </>
        )}
      </div>
      {error && <span className="text-[11px] text-[var(--status-error)] mt-0.5">{error}</span>}
      {success && <span className="text-[11px] text-[var(--status-success)] mt-0.5">{success}</span>}
    </div>
  );
}
```

**使用示例**：
```tsx
// 替换 ProfilePage 中的 Email 和 Itcode 编辑块
<InlineEditField
  label="邮箱"
  value={userInfo.email}
  onSave={async (val) => {
    const res = await api.updateUser(userInfo.user_id, { email: val || undefined });
    if (res.code !== 0 && res.code !== 200) throw new Error(res.message || '更新邮箱失败');
  }}
  validator={(val) => val && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val) ? '邮箱格式不正确' : true}
  placeholder="输入邮箱地址"
/>

<InlineEditField
  label="光圈通知 itcode"
  value={userInfo.itcode}
  onSave={async (val) => {
    const res = await api.updateUser(userInfo.user_id, { itcode: val || undefined });
    if (res.code !== 0 && res.code !== 200) throw new Error(res.message || '更新 itcode 失败');
  }}
  placeholder="输入 itcode"
  successText="通知 itcode 已更新"
/>
```

---

### 5.2 提取 `ToggleSwitch` 组件

**位置**：`frontend/src/components/ProfilePage.tsx:429-441`

**优化方案**：

```tsx
// components/ui/ToggleSwitch.tsx
interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  labels?: [string, string]; // [checkedLabel, uncheckedLabel]
}

export default function ToggleSwitch({ checked, onChange, disabled, labels }: ToggleSwitchProps) {
  return (
    <label className="flex items-center gap-2 cursor-pointer" aria-label="开关">
      <div
        role="switch"
        aria-checked={checked}
        onClick={() => !disabled && onChange(!checked)}
        className={`relative w-10 h-5.5 rounded-full transition-colors duration-200 ${
          checked ? 'bg-[#3fb950]' : 'bg-[var(--border-default)]'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <div className={`absolute top-0.5 w-[18px] h-[18px] rounded-full bg-white shadow transition-all duration-200 ${
          checked ? 'left-5' : 'left-0.5'
        }`} />
      </div>
      {labels && <span className="text-[13px]">{checked ? labels[0] : labels[1]}</span>}
    </label>
  );
}
```

**使用示例**：
```tsx
<ToggleSwitch
  checked={userInfo.subscribe_notifications}
  onChange={async (newVal) => {
    await api.updateUser(userInfo.user_id, { subscribe_notifications: newVal });
    setUserInfo({ ...userInfo, subscribe_notifications: newVal });
  }}
  disabled={savingSubscription}
  labels={['已订阅', '未订阅']}
/>
```

---

## 六、实施路线图建议

### 阶段 1：立即修复（1-2 天）
- [ ] 删除 `types/index.ts` 中第 1206-1253 行的重复定义（P0）
- [ ] 创建 `components/ui/Modal.tsx` 并在 `ProfilePage.tsx` 中试用（P1）
- [ ] 创建 `components/ui/Card.tsx`、`LoadingSpinner.tsx`、`ErrorBanner.tsx`（P1）

### 阶段 2：核心重构（1 周）
- [ ] 拆分 `TestExecutionPlanDemo.tsx` 到 `components/execution-plan/` 目录（P0）
- [ ] 提取 `theme.ts` 统一状态颜色（P1）
- [ ] 在 `ProfilePage.tsx` 中用 Tailwind 类替换内联样式（P1 试点）
- [ ] 创建 `InlineEditField.tsx` 和 `ToggleSwitch.tsx`（P3）

### 阶段 3：架构统一（2 周）
- [ ] 将 `ProfilePage.tsx` 迁移到 TanStack Query（P2）
- [ ] 拆分 `types/index.ts` 为 domain 文件（P2）
- [ ] 拆分 `services/api.ts` 为 domain 文件（P2）
- [ ] 推广 `Modal` 和 `Card` 到其他页面组件（P1）

### 阶段 4：全面推广（持续）
- [ ] 将所有页面组件从手动 `useState` 请求迁移到 TanStack Query（P2）
- [ ] 将所有页面组件的内联样式迁移到 Tailwind（P1）
- [ ] 建立 UI 组件库规范文档（P3）

---

## 七、验收标准

| 检查项 | 通过标准 |
|--------|----------|
| `types/index.ts` 重复定义 | 不存在同一接口的重复定义 |
| `TestExecutionPlanDemo.tsx` | 文件行数 < 400 行，子组件均已独立提取 |
| Modal 弹窗 | 所有弹窗使用 `components/ui/Modal.tsx` |
| Card / Loading / Error | 页面级 `styles` 对象中不存在 `card`、`loadingState`、`errorBanner` 定义 |
| 状态颜色 | 不存在硬编码的 `rgba(63,185,80,0.08)` 或 `#3fb950` 散落于业务组件中 |
| 数据请求 | 新页面/重构页面使用 `useQuery` 而非 `useState` + `useEffect` |
| 类型文件 | `types/index.ts` 行数 < 200 行，domain 类型已按模块拆分 |

---

## 附录：相关文件清单

| 文件 | 当前问题 | 优化优先级 |
|------|----------|-----------|
| `frontend/src/components/TestExecutionPlanDemo.tsx` | 2607 行，14 个组件混杂 | P0 |
| `frontend/src/types/index.ts` | 1459 行，存在重复定义 | P0 |
| `frontend/src/components/ProfilePage.tsx` | 内联样式、重复编辑逻辑、手动请求 | P1/P2/P3 |
| `frontend/src/components/RequirementsPage.tsx` | 内联样式、手动请求 | P1/P2 |
| `frontend/src/components/UserManagement.tsx` | 1857 行，但已使用 TanStack Query（良好） | P1（拆分） |
| `frontend/src/components/LoginPage.tsx` | 内联样式 | P1 |
| `frontend/src/components/AppShell.tsx` | 内联样式 | P1 |
| `frontend/src/services/api.ts` | 单体类，100+ 方法 | P2 |
| `frontend/src/components/ui/PageHero.tsx` | 良好（已复用） | — |
| `frontend/src/components/ui/PageToolbar.tsx` | 良好（已复用） | — |
