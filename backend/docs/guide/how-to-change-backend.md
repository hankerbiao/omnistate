# 如何修改后端

这篇文档回答的是“我要改一个需求，应该先看哪里”。

## 改接口

先看对应模块的 `api/`：

- 路由定义
- 依赖注入
- request/response schema

通常路径是：

- `app/modules/<module>/api/routes*.py`
- `app/modules/<module>/api/dependencies.py`

## 改业务规则

优先看：

- `application/`
- `service/`
- `domain/`

判断原则：

- 规则判断、策略、异常：通常在 `domain/`
- 用例编排：通常在 `application/`
- 直接实体读写和资源逻辑：通常在 `service/`

## 改 workflow 状态机

优先看：

- `app/configs/*.json`
- `app/modules/workflow/application/mutation_service.py`
- `app/modules/workflow/domain/rules.py`
- `app/modules/workflow/domain/policies.py`

如果是配置问题，先改 JSON；
如果是行为问题，再改 mutation/domain。

## 改需求或用例

优先看：

- `app/modules/test_specs/application/*command_service.py`
- `app/modules/test_specs/service/requirement_service.py`
- `app/modules/test_specs/service/test_case_service.py`

如果涉及 workflow 状态投影或显式命令，顺便看 `test_specs/service/_service_support.py`。

## 改执行任务

优先看：

- 创建/删除/重跑任务：`task_command_service.py`
- 查询与序列化：`task_query_service.py`
- 真正下发：`task_dispatch_service.py`
- case 解析与快照：`task_case_mixin.py`
- 事件回填：`event_ingest_service.py`

## 改鉴权

优先看：

- `app/shared/auth/*`
- `app/modules/auth/api/dependencies.py`
- `app/modules/auth/service/*`

现在 `auth` 以资源级 service 为主，不再通过单一大 facade 汇总。

## 改共享约定

优先看：

- 日志：`app/shared/core/logger.py`
- Mongo 客户端：`app/shared/core/mongo_client.py`
- 统一响应与异常：`app/shared/api/*`
- 配置：`app/shared/db/config.py`
