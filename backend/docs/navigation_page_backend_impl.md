# 导航页管理后端实现说明

更新时间：2026-03-02

## 1. 目标

- 将原先写死在服务中的 `_NAVIGATION_PAGES` 下沉到数据库。
- 提供导航页管理能力（管理员可查/增/改/删）。
- 保持现有用户导航接口可用：`/api/v1/auth/users/me/navigation`。

## 2. 数据模型

文件：`app/modules/auth/repository/models/navigation.py`

新增集合：`navigation_pages`

字段说明：

- `view`：导航唯一标识（唯一索引）
- `label`：导航展示名称
- `permission`：访问该导航所需权限码（可为空）
- `description`：导航说明
- `order`：排序（越小越靠前）
- `is_active`：是否启用
- `is_deleted`：逻辑删除标记
- `created_at` / `updated_at`

## 3. 默认数据初始化

默认导航定义常量：

- `DEFAULT_NAVIGATION_PAGES`
  文件：`app/modules/auth/service/navigation_page_service.py`

初始化时机：

1. 运行初始化脚本：`python backend/app/init_mongodb.py`
2. 服务运行时读取导航定义时自动兜底（幂等 upsert）

初始化脚本新增函数：

- `init_navigation_pages()`
  文件：`app/init_mongodb.py`

## 4. 服务层改造

### 4.1 新增导航管理服务

文件：`app/modules/auth/service/navigation_page_service.py`

主要能力：

- `ensure_default_pages()`: 默认导航幂等写入
- `list_pages(include_inactive=True)`: 查询导航页
- `list_active_pages()`: 查询启用导航页
- `get_page(view)`: 查询单页
- `create_page(data)`: 创建
- `update_page(view, data)`: 更新
- `delete_page(view)`: 逻辑删除

### 4.2 RbacService 改为数据库驱动

文件：`app/modules/auth/service/rbac_service.py`

改造点：

- 不再依赖硬编码 `_NAVIGATION_PAGES`
- `list_navigation_pages()` 改为调用 `NavigationPageService`
- `get_user_navigation()` 改为基于数据库导航定义计算可访问 `allowed_nav_views`
- `update_user_navigation()` 仅允许保存当前有效导航集内的 view
- 保持 `my_tasks` 为全员强制可见（`_MANDATORY_NAV_VIEWS`）

## 5. 新增管理员导航管理接口

文件：`app/modules/auth/api/routes.py`

在原有接口基础上新增：

- `GET /api/v1/auth/admin/navigation/pages/{view}`：导航页详情
- `POST /api/v1/auth/admin/navigation/pages`：创建导航页
- `PUT /api/v1/auth/admin/navigation/pages/{view}`：更新导航页
- `DELETE /api/v1/auth/admin/navigation/pages/{view}`：删除导航页（逻辑删除）

已有接口增强：

- `GET /api/v1/auth/admin/navigation/pages?include_inactive=true|false`

## 6. 前端联调建议

1. 首次联调先执行初始化脚本，确保 `navigation_pages` 已有默认数据。
2. 配置页建议调用：
   - 列表：`GET /admin/navigation/pages?include_inactive=true`
   - 保存：`POST/PUT/DELETE /admin/navigation/pages...`
3. 用户侧导航继续使用：
   - `GET /users/me/navigation`
4. 如果某导航页 `is_active=false` 或已删除，用户端返回的 `allowed_nav_views` 将不会包含该项。
