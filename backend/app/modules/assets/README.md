# 资产管理模块（assets）

本模块负责 **硬件与资产管理层** 的数据管理，涵盖硬件部件字典、设备资产（DUT）以及测试计划关联部件。

## 主要职责
- 维护硬件部件字典（Component Library）
- 管理设备资产（DUT）台账与状态
- 维护测试计划与部件的关联关系
- 提供 CRUD 接口与查询能力

## 目录结构
- `api/`：HTTP 路由层（FastAPI）
- `schemas/`：API 请求/响应模型
- `service/`：领域服务逻辑
- `repository/models/`：Beanie 文档模型与 Pydantic 模型

## 核心模型
- `ComponentLibraryDoc`：部件字典
- `DutDoc`：设备资产
- `TestPlanComponentDoc`：测试计划关联部件

## API 概览
- 部件字典：`/api/v1/assets/components`
- 设备资产：`/api/v1/assets/duts`
- 计划关联部件：`/api/v1/assets/plan-components`

## 设备录入字段说明
当前创建设备资产使用 `POST /api/v1/assets/duts`，对应请求模型为 `CreateDutRequest`。

必填字段：
- `asset_id`：资产编号或设备 SN，必须唯一
- `model`：整机型号或平台名称

选填字段：
- `status`：设备状态，默认 `可用`
- `owner_team`：归属团队或项目
- `rack_location`：机房、机柜、机位信息
- `bmc_ip`：BMC 管理 IP
- `bmc_port`：BMC 端口
- `os_ip`：操作系统业务 IP
- `os_port`：操作系统 SSH 或访问端口
- `login_username`：登录用户名
- `login_password`：登录密码
- `health_status`：健康状态
- `notes`：备注

系统自动生成字段：
- `created_at`
- `updated_at`

建议最少录入：
- `asset_id`
- `model`
- `owner_team`
- `rack_location`
- 至少一组可访问地址：`bmc_ip` 或 `os_ip`

## 备注
- 所有时间字段统一使用 UTC。
- 部件与资产的唯一键：`part_number` / `asset_id`。
