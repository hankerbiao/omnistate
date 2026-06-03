# 排障手册

## 服务启动失败

优先检查：

1. `app/main.py`
2. Mongo 连接配置
3. workflow 配置一致性校验
4. 路由导入是否在启动时抛异常

常见现象：

- Mongo ping 失败
- workflow 初始化数据缺失
- FastAPI 路由组合错误

## workflow 相关问题

现象：

- 不能流转
- 必填字段报错
- 当前状态下无可用动作

优先检查：

- `app/configs/*.json`
- `SysWorkflowConfigDoc`
- `workflow/domain/rules.py`
- `workflow/domain/policies.py`

## requirement / test case 状态不对

现象：

- 业务文档正常，但接口返回状态异常

优先检查：

- `test_specs/service/_workflow_status_support.py`
- `test_specs/service/_service_support.py`
- workflow 事项是否存在
- 业务文档的 `workflow_item_id` 是否正确

## execution 任务不推进

现象：

- 任务一直停在当前 case
- 事件消费了但任务状态没更新
- 第一条 case 完成后没有下发第二条

优先检查：

- `execution/application/event_ingest_service.py`
- `execution/application/progress_coordinator.py`
- `execution/application/task_dispatch_service.py`
- `ExecutionTaskDoc` / `ExecutionTaskCaseDoc` / `ExecutionEventDoc`
- Kafka Worker 进程是否在运行

结构化排障（推荐）：

1. `GET /api/v1/execution/tasks/{task_id}/biz-logs` 看平台节点时间线
2. `cat logs/execution.log | jq 'select(.task_id=="...")'` 看 `task.advance` 是否 `skipped`
3. MongoDB `execution_events` 确认是否有 `case_finish` 且 `case_id` 等于 `current_case_id`

完整 Runbook：[Execution 日志与排障](/modules/execution/logging)。

## execution 下发异常

现象：

- `dispatch_status=DISPATCH_FAILED`
- Agent 未收到任务

优先检查：

- `execution/service/task_dispatcher.py`
- `config.yaml` 中 `rabbitmq` 连接与队列配置
- 日志节点 `task.dispatch`
- RabbitMQ 队列是否可达、Agent 是否正常消费

详见 [Execution Worker 与消息](/modules/execution/workers)。

## 鉴权失败

现象：

- 登录成功但接口 403
- 导航权限不正确

优先检查：

- `app/shared/auth/jwt_auth.py`
- `app/modules/auth/service/user_service.py`
- `app/modules/auth/service/navigation_access_service.py`
- 角色、权限、导航初始化数据
