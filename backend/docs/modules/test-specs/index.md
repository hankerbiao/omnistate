# Test Specs 模块

## 模块职责

`test_specs` 负责定义和管理：

- 测试需求
- 测试用例
- 自动化测试用例

它是业务定义层，同时负责把 workflow 状态投影到需求和用例响应上。

## 核心目录

- `api/`
  路由和依赖注入
- `application/`
  requirement/test case 命令服务与 query service
- `service/`
  RequirementService、TestCaseService、AutomationTestCaseService
- `service/_service_support.py`
  共性 support：状态投影、workflow-aware 删除、事务模板
- `repository/models/`
  需求、用例、自动化用例模型

## 核心模型

- `TestRequirementDoc`
- `TestCaseDoc`
- `AutomationTestCaseDoc`

## 关键字段说明

### `TestRequirementDoc`

- `req_id`
  需求业务 ID，对外主识别字段
- `workflow_item_id`
  对应的 workflow 事项 ID，用于状态投影
- `tpm_owner_id`
  需求负责人之一，通常也是创建 workflow 事项时的创建人来源
- `manual_dev_id`
  手工测试开发负责人
- `auto_dev_id`
  自动化开发负责人
- `is_deleted`
  逻辑删除标记

### `TestCaseDoc`

- `case_id`
  用例业务 ID
- `ref_req_id`
  归属需求 ID
- `workflow_item_id`
  关联 workflow 事项 ID
- `owner_id`
  用例负责人
- `reviewer_id`
  审核人
- `auto_dev_id`
  自动化开发负责人
- `attachments`
  附件列表，创建时会被校验并补齐元数据
- `is_deleted`
  逻辑删除标记

### `AutomationTestCaseDoc`

- `auto_case_id`
  自动化用例业务 ID
- `dml_manual_case_id`
  对应平台手工用例 ID
- `script_path`
  执行脚本路径
- `script_name`
  执行脚本名称
- `script_ref`
  脚本资源引用，用于 execution 下发时解析实体

## 关键关系

- `TestCaseDoc.ref_req_id` 指向需求
- 业务文档通过 `workflow_item_id` 关联 workflow 事项
- 自动化用例和手工用例通过 `auto_case_id` / `dml_manual_case_id` 对应

## 关键调用链

- requirement 创建：
  command service -> `RequirementService` -> workflow gateway -> Mongo 事务
- test case 创建：
  command service -> `TestCaseService` -> requirement 校验 -> workflow gateway -> Mongo 事务
- 列表查询：
  query service -> service -> workflow 状态投影

## 关键业务规则

- `status` 是 workflow 投影字段，不允许直接更新
- 高风险字段必须走显式命令
- 已绑定 workflow 的 requirement / test case 不能走普通删除路径
- requirement 删除前必须确认没有未删除 test case

## 常见修改场景

- 改 requirement/test case 可编辑字段：看对应 service 的 `_UPDATABLE_FIELDS`
- 改状态投影逻辑：看 `_service_support.py` 和 `_workflow_status_support.py`
- 改显式命令：看 `application/*command_service.py`

## 风险点

- 业务文档和 workflow 事项不一致时，状态会表现异常
- requirement / case 的联动规则分散在 command service 和 service 层，改动时要双向核对
