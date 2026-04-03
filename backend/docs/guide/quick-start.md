# 快速开始

这篇文档面向第一次接手 DML V4 后端的人，目标是在最短时间内建立正确心智模型。

## 项目是什么

这是一个基于 FastAPI + MongoDB + Beanie 的后端服务，核心业务围绕：

- 工作流状态机
- 测试需求与测试用例
- 执行任务编排
- RBAC 鉴权

统一 API 前缀是 `/api/v1`。

## 目录怎么读

- `app/main.py`
  服务入口，负责 Mongo、Beanie、基础设施初始化
- `app/modules/*`
  业务模块
- `app/shared/*`
  跨模块共用能力
- `app/configs/*`
  workflow 初始化配置
- `scripts/*`
  初始化与运维脚本
- `tests/*`
  单元测试与架构约束测试

## 先建立什么心智模型

- `workflow` 是底层业务流转基础设施
- `test_specs` 是需求与用例定义层，依赖 `workflow`
- `execution` 是执行编排层，依赖 `test_specs`
- `auth` 为所有模块提供鉴权能力

不要把它理解成“很多独立小服务”，它目前仍是一个统一的 FastAPI 单体后端。

## RBAC 是什么，为什么这里需要它

这里的 `RBAC` 指的是 `Role-Based Access Control`，也就是“基于角色的访问控制”。

在 DML V4 后端里，RBAC 的存在不是为了做一个抽象的权限系统，而是为了控制不同角色在测试平台中的可操作边界。例如：

- 谁可以创建或编辑测试需求
- 谁可以流转工作项状态
- 谁可以下发执行任务
- 谁可以管理用户、角色、权限和导航

如果没有 RBAC，这些能力只能靠前端隐藏按钮或者后端硬编码用户判断，后续一旦角色变多、功能变多，权限就会迅速失控。

## RBAC 和 JWT 的关系

这两个概念要分开看：

- `JWT`
  解决“你是谁”，也就是认证
- `RBAC`
  解决“你能做什么”，也就是授权

当前后端的基本链路是：

1. 用户登录后获得 JWT
2. 后端通过 JWT 解析出当前用户
3. 再根据用户绑定的角色，聚合出权限码
4. 路由通过 `require_permission(...)` 或 `require_any_permission(...)` 校验是否允许访问

所以，JWT 是入口票据，RBAC 是访问控制规则。

## 当前 RBAC 在这个后端里的落点

RBAC 相关能力主要由 `auth` 模块和 `app/shared/auth/*` 共同完成：

- `auth` 模块负责用户、角色、权限、导航等资源管理
- `app/shared/auth/jwt_auth.py` 负责 JWT 解析、当前用户获取和权限校验依赖

你可以把它理解成两层：

- 管理层：谁拥有哪些角色、角色拥有哪些权限
- 运行层：请求进来后如何把这些角色和权限真正执行起来

## RBAC 里最关键的字段

如果你要读代码或查库，先认识下面这些字段：

### 用户（`UserDoc`）

- `user_id`
  用户业务主键，对外识别用户时优先使用它，不直接暴露 Mongo `ObjectId`
- `username`
  登录名或展示名
- `role_ids`
  用户绑定的角色列表，RBAC 权限计算从这里开始
- `allowed_nav_views`
  用户级导航可见范围覆盖；为空时通常回退到角色/权限默认逻辑
- `status`
  用户状态，当前用户校验时会检查是否为 `ACTIVE`

### 角色（`RoleDoc`）

- `role_id`
  角色业务主键
- `permission_ids`
  角色绑定的权限 ID 列表，用于聚合用户有效权限

### 权限（`PermissionDoc`）

- `perm_id`
  权限业务主键
- `code`
  权限码，当前后端约定采用 `resource:action` 形式，例如 `requirements:read`
- `name`
  权限名称，偏展示用途

### 导航（`NavigationPageDoc`）

- `view`
  导航页面唯一标识
- `permission`
  页面访问权限码；可以是公共页面，也可以要求特定权限
- `is_active`
  页面是否启用
- `is_deleted`
  逻辑删除标记

## JWT / RBAC 相关配置项

这些配置主要在 `app/shared/db/config.py` 中定义，接手时至少知道它们的作用：

- `JWT_SECRET_KEY`
  JWT 签名密钥；变更后旧 token 会失效
- `JWT_ALGORITHM`
  当前签名算法，代码里目前按 `HS256` 处理
- `JWT_EXPIRE_MINUTES`
  token 过期时间，单位分钟
- `JWT_ISSUER`
  token 的签发者校验值
- `JWT_AUDIENCE`
  token 的受众校验值

这些配置主要影响：

- 登录后发出的 token 是否能被后端正确校验
- 不同环境之间 token 是否兼容
- token 过期和鉴权失败时的行为

## 接手时先知道哪些事实

- 权限码采用 `resource:action` 形式，例如 `requirements:read`
- 管理员权限有显式放行逻辑，不完全走普通权限集合判断
- 导航访问控制也是 `auth` 模块的一部分，不只是接口权限
- 如果你改了业务接口，但没有补对应权限依赖，等于绕开了 RBAC

## 最短接手路径

1. 先看 [本地开发](./local-development.md) 跑通服务
2. 再看 [架构总览](./architecture-overview.md) 认识整体结构
3. 再看 [如何修改后端](./how-to-change-backend.md) 知道改动入口
4. 最后进入对应模块页看实现细节
