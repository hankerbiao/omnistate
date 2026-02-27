# 工作流模块（Workflow Module）

本模块提供 **配置驱动的工作流引擎**，基于 MongoDB + Beanie ODM 实现。
支持业务事项管理、状态机流转、流转日志审计，并提供对应的 API 接口。

## 主要职责
- 维护流程配置（事项类型、状态、流转规则）
- 管理业务事项（Work Item）及其状态机流转
- 记录每一次流转日志，满足审计需求
- 提供 API：CRUD + 流转操作 + 查询

## 目录结构
- `api/`：HTTP 路由层（FastAPI）
- `schemas/`：API 请求/响应模型
- `service/`：工作流核心服务逻辑
- `repository/models/`：Beanie 文档模型与 Pydantic 模型
- `domain/`：规则校验与异常定义
- `docs/`：模块文档

## 核心模型
- `SysWorkTypeDoc`：事项类型配置
- `SysWorkflowStateDoc`：流程状态配置
- `SysWorkflowConfigDoc`：流转规则配置
- `BusWorkItemDoc`：业务事项
- `BusFlowLogDoc`：流转日志

## 数据流说明
1. **初始化**：通过 `app/init_mongodb.py` 读取 `app/configs/*.json` 配置并同步到 MongoDB。
2. **事项创建**：创建业务事项后进入初始状态。
3. **状态流转**：依据 `SysWorkflowConfigDoc` 校验流转合法性及必填字段。
4. **流转日志**：每次流转写入 `BusFlowLogDoc`，包含操作人、动作与表单载荷。

## API 概览
- 事项 CRUD
- 获取事项类型 / 状态 / 流转配置
- 状态流转与流转历史查询

路由已在 `app/shared/api/main.py` 中挂载，前缀为：
- `/api/v1/work-items`

## 备注
- 所有时间字段统一使用 UTC。
- 流转校验与必填字段检查集中在 `domain/rules.py`。
