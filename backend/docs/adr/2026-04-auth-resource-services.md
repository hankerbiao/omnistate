# ADR: Auth 资源级服务拆分

日期：2026-04-02

## 背景

原有 `RbacService` 同时承担：

- 用户 CRUD / 密码 / 角色绑定
- 角色 CRUD / 权限绑定
- 权限 CRUD
- 导航页面 CRUD
- 用户导航可见性推导

这导致 service 体量过大，路由层全部依赖同一个 facade，边界不清晰。

## 决策

将 auth 应用逻辑拆成资源级 service：

- `UserService`
- `RoleService`
- `PermissionService`
- `NavigationAccessService`

API 路由按资源直接依赖对应 service。  
删除 `RbacService` 兼容 facade，API 与调用方统一直接依赖资源级 service。

## 结果

- 路由依赖和资源边界一致
- 彻底消除 facade 回流风险
- 后续可以逐步淘汰 facade，而不影响当前 API

## 放弃方案

- 保留单一 `RbacService`，只靠注释和方法分组维持可读性
- 保留 `RbacService` 作为兼容 facade，继续做旧入口转发
- 再拆一个更大的 “AuthApplicationService” 聚合所有资源
