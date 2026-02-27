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

## 备注
- 所有时间字段统一使用 UTC。
- 部件与资产的唯一键：`part_number` / `asset_id`。
