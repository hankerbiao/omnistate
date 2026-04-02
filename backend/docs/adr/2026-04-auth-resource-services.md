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
`RbacService` 降级为兼容 facade，仅做委托，不再承载新增逻辑。

## 结果

- 路由依赖和资源边界一致
- `RbacService` 体量显著收缩
- 后续可以逐步淘汰 facade，而不影响当前 API

## 放弃方案

- 保留单一 `RbacService`，只靠注释和方法分组维持可读性
- 再拆一个更大的 “AuthApplicationService” 聚合所有资源
