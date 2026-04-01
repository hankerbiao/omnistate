# 服务器管理看板 - 设计方案

## 1. 项目概述

一个用于记录和管理服务器信息的 Web 应用，类似"服务器备忘录"，可以记录服务器的 IP、密码、运行的服务等信息，方便日常查询和维护。

## 2. 技术架构

| 层级 | 技术选型 |
|------|----------|
| 后端 | Python FastAPI + SQLite |
| 前端 | React 18 + TypeScript + Vite |
| 样式 | Tailwind CSS 4 |
| 状态管理 | React Context + Hooks |

## 3. 数据模型

### 服务器 (Server)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | string | 服务器名称/别名 |
| ip | string | IP 地址 |
| port | number | SSH 端口（默认22） |
| username | string | 用户名 |
| password | string | 密码（明文） |
| description | string | 备注描述 |
| location | string | 服务器位置/机房 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 服务 (Service)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| server_id | UUID | 关联服务器 |
| name | string | 服务名称 |
| type | string | 服务类型（Web/API/DB/Cache 等） |
| url | string | 访问 URL（可选） |
| port | number | 服务端口 |
| description | string | 服务描述 |
| created_at | datetime | 创建时间 |

## 4. API 设计

### 服务器管理
- `GET /api/servers` - 获取服务器列表
- `POST /api/servers` - 创建服务器
- `GET /api/servers/{id}` - 获取服务器详情
- `PUT /api/servers/{id}` - 更新服务器
- `DELETE /api/servers/{id}` - 删除服务器

### 服务管理
- `GET /api/servers/{id}/services` - 获取服务器的所有服务
- `POST /api/servers/{id}/services` - 添加服务
- `PUT /api/services/{id}` - 更新服务
- `DELETE /api/services/{id}` - 删除服务

## 5. 前端页面设计

### 页面结构（单页面应用）

```
+----------------------------------------------------------+
|  Header: Logo + 标题 + 添加服务器按钮                    |
+----------------------------------------------------------+
|  Sidebar        |  Main Content                         |
|  +-----------+  |  +--------------------------------+   |
|  | 服务器列表 |  |  | 服务器详情 / 服务列表          |   |
|  | - Server1 |  |  |                                |   |
|  | - Server2 |  |  | IP: xxx                        |   |
|  | - Server3 |  |  | 密码: xxx                      |   |
|  +-----------+  |  | 服务:                          |   |
|                 |  |   - Nginx (80)                 |   |
|                 |  |   - MySQL (3306)               |   |
|                 |  +--------------------------------+   |
+----------------------------------------------------------+
```

### 核心功能
1. **服务器列表** - 左侧 sidebar，显示所有服务器，点击选中
2. **服务器详情** - 右侧主区域，展示服务器信息和关联服务
3. **添加/编辑弹窗** - Modal 形式录入服务器信息
4. **服务管理** - 在服务器详情中添加、编辑、删除服务
5. **搜索过滤** - 支持按名称/IP 搜索服务器

### UI 风格
- 深色主题（Dark Mode）
- 现代化卡片设计，圆角阴影
- 微交互：hover 效果、过渡动画
- 简洁的图标（使用 Lucide React）