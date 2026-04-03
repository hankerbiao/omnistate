# 数据库表与字段

这篇文档面向开发和交接场景，回答两个问题：

- 当前后端到底落了哪些 MongoDB 集合
- 每张表里最重要的字段是什么，分别承担什么职责

下面的“表”统一指 Beanie `Document` 对应的 MongoDB collection。

## Workflow 相关表

### `sys_work_types`

对应模型：`SysWorkTypeDoc`

- `code`
  事项类型编码，唯一键
- `name`
  事项类型名称
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 定义系统支持的工作项类型，例如需求、测试用例等

### `sys_workflow_states`

对应模型：`SysWorkflowStateDoc`

- `code`
  状态编码，唯一键
- `name`
  状态名称
- `is_end`
  是否为终态
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 定义状态机中的所有合法状态

### `sys_workflow_configs`

对应模型：`SysWorkflowConfigDoc`

- `type_code`
  适用的事项类型
- `from_state`
  当前状态
- `action`
  可执行动作
- `to_state`
  目标状态
- `target_owner_strategy`
  流转后处理人策略
- `required_fields`
  本次动作要求的表单字段
- `properties`
  扩展属性
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 这是 workflow 状态机的核心配置表，决定某类型事项在某状态下执行某动作时如何流转

### `bus_work_items`

对应模型：`BusWorkItemDoc`

- `type_code`
  事项类型
- `title`
  标题
- `content`
  内容或描述
- `parent_item_id`
  父事项 ID
- `current_state`
  当前状态，workflow 真实状态来源
- `current_owner_id`
  当前处理人
- `creator_id`
  创建人
- `is_deleted`
  逻辑删除标记
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 存储真实的业务流转主体

### `bus_flow_logs`

对应模型：`BusFlowLogDoc`

- `work_item_id`
  对应事项 ID
- `from_state`
  变更前状态
- `to_state`
  变更后状态
- `action`
  触发动作
- `operator_id`
  操作人
- `payload`
  本次流转携带的数据
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 记录每一次状态变更、改派、删除等操作的审计轨迹

## Test Specs 相关表

### `test_requirements`

对应模型：`TestRequirementDoc`

- `req_id`
  需求业务 ID
- `workflow_item_id`
  对应 workflow 事项 ID
- `title`
  需求标题
- `description`
  需求说明
- `technical_spec`
  技术规范
- `target_components`
  目标部件列表
- `firmware_version`
  固件版本
- `priority`
  优先级
- `key_parameters`
  关键参数列表
- `risk_points`
  风险点
- `tpm_owner_id`
  TPM/创建人
- `manual_dev_id`
  手工测试负责人
- `auto_dev_id`
  自动化负责人
- `attachments`
  附件列表
- `is_deleted`
  逻辑删除
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 管理测试需求主体，并通过 `workflow_item_id` 关联到 workflow 状态机

### `test_cases`

对应模型：`TestCaseDoc`

- `case_id`
  用例业务 ID
- `ref_req_id`
  所属需求 ID
- `workflow_item_id`
  对应 workflow 事项 ID
- `title`
  用例标题
- `version`
  版本号
- `is_active`
  是否是当前有效版本
- `change_log`
  版本变更说明
- `owner_id`
  责任人
- `reviewer_id`
  审核人
- `auto_dev_id`
  自动化负责人
- `priority`
  优先级
- `estimated_duration_sec`
  预估时长（秒）
- `required_env`
  环境要求
- `tags`
  标签
- `test_category`
  测试分类
- `is_destructive`
  是否破坏性测试
- `pre_condition`
  前置条件
- `post_condition`
  后置条件
- `risk_level`
  风险等级
- `failure_analysis`
  失败分析建议
- `confidentiality`
  机密等级
- `visibility_scope`
  可见范围
- `attachments`
  附件列表
- `custom_fields`
  自定义字段
- `deprecation_reason`
  废弃原因
- `approval_history`
  审批记录
- `is_deleted`
  逻辑删除
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 管理平台测试用例主体，并承载需求关联、workflow 状态投影源和执行前置元数据

### `automation_test_cases`

对应模型：`AutomationTestCaseDoc`

- `auto_case_id`
  自动化用例业务 ID
- `dml_manual_case_id`
  关联的手工测试用例 ID
- `name`
  自动化用例名称
- `description`
  描述
- `status`
  状态，例如 `ACTIVE`
- `framework`
  上报框架类型
- `automation_type`
  自动化类型
- `script_ref`
  脚本定位信息
- `config_path`
  配置文件路径
- `script_name`
  脚本文件名
- `script_path`
  脚本文件路径
- `code_snapshot`
  代码版本快照
- `param_spec`
  参数定义
- `tags`
  标签
- `report_meta`
  上报补充信息
- `is_deleted`
  逻辑删除
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 保存当前可执行的自动化用例元数据，供 execution 下发前解析脚本和参数

## Execution 相关表

### `execution_tasks`

对应模型：`ExecutionTaskDoc`

- `task_id`
  任务业务 ID
- `source_task_id`
  重跑来源任务 ID
- `framework`
  执行框架
- `agent_id`
  目标代理 ID
- `dispatch_channel`
  下发通道
- `dedup_key`
  去重键
- `schedule_type`
  调度类型
- `schedule_status`
  调度状态
- `dispatch_status`
  下发状态
- `consume_status`
  消费状态
- `overall_status`
  任务整体状态
- `request_payload`
  原始任务快照
- `dispatch_response`
  下发响应快照
- `dispatch_error`
  下发失败原因
- `created_by`
  创建人 `user_id`
- `case_count`
  任务包含的 case 数量
- `reported_case_count`
  已上报进度的 case 数量
- `started_case_count`
  已开始执行的 case 数量
- `finished_case_count`
  已执行完成的 case 数量
- `passed_case_count`
  已通过数量
- `failed_case_count`
  已失败数量
- `progress_percent`
  任务进度
- `current_case_id`
  当前推进的 case
- `current_case_index`
  当前 case 序号
- `planned_at`
  计划触发时间
- `triggered_at`
  首次真正下发时间
- `started_at`
  任务开始时间
- `finished_at`
  任务结束时间
- `last_callback_at`
  最近一次执行端回调时间
- `last_event_at`
  最近一次事件时间
- `last_event_id`
  最近一次事件 ID
- `last_event_type`
  最近一次事件类型
- `last_event_phase`
  最近一次事件阶段
- `consumed_at`
  下游消费者确认消费时间
- `is_deleted`
  逻辑删除
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 这是执行任务的当前态主表，查任务整体状态优先看它

### `execution_task_cases`

对应模型：`ExecutionTaskCaseDoc`

- `task_id`
  所属任务 ID
- `case_id`
  平台测试用例 ID
- `case_snapshot`
  case 快照
- `order_no`
  在任务中的顺序
- `dispatch_status`
  平台下发状态
- `dispatch_attempts`
  下发次数
- `status`
  当前 case 状态
- `progress_percent`
  当前 case 进度
- `step_total`
  总步骤数
- `step_passed`
  已通过步骤数
- `step_failed`
  已失败步骤数
- `step_skipped`
  已跳过步骤数
- `last_seq`
  最近已处理事件序号
- `last_event_id`
  最近事件 ID
- `last_event_at`
  最近事件时间
- `event_count`
  事件数量
- `started_at`
  case 开始时间
- `finished_at`
  case 结束时间
- `dispatched_at`
  最近一次下发时间
- `failure_message`
  失败信息
- `nodeid`
  测试节点标识
- `project_tag`
  项目标签
- `case_title_snapshot`
  用例标题快照
- `result_data`
  当前 case 结果摘要
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 这是任务内单条 case 的当前态表，查“卡在哪个 case”优先看它

### `execution_events`

对应模型：`ExecutionEventDoc`

- `event_id`
  事件唯一 ID
- `task_id`
  任务 ID
- `case_id`
  测试用例 ID
- `topic`
  Kafka topic
- `schema_name`
  事件 schema 名称
- `event_type`
  事件类型
- `phase`
  事件阶段
- `event_seq`
  事件顺序号
- `event_status`
  事件状态
- `event_timestamp`
  事件原始时间
- `payload`
  原始事件载荷
- `metadata`
  Kafka 元数据
- `processed`
  是否已处理成功
- `process_error`
  处理失败原因
- `ingested_at`
  入库时间
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 这是执行事件归档表，负责幂等、审计和排障

### `execution_agents`

对应模型：`ExecutionAgentDoc`

- `agent_id`
  代理唯一标识
- `hostname`
  主机名
- `ip`
  代理 IP
- `port`
  代理端口
- `base_url`
  代理服务地址
- `region`
  所属区域
- `status`
  代理状态
- `registered_at`
  最近注册时间
- `last_heartbeat_at`
  最近心跳时间
- `heartbeat_ttl_seconds`
  心跳过期阈值
- `is_deleted`
  逻辑删除
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 保存可接收执行任务的 agent 注册信息和在线状态

## Auth 相关表

### `users`

对应模型：`UserDoc`

- `user_id`
  用户业务 ID
- `username`
  用户名
- `email`
  邮箱
- `password_hash`
  密码哈希
- `password_salt`
  密码盐
- `role_ids`
  角色 ID 列表
- `allowed_nav_views`
  用户级导航覆盖
- `status`
  用户状态
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 保存用户主体和用户与角色的绑定关系

### `roles`

对应模型：`RoleDoc`

- `role_id`
  角色业务 ID
- `name`
  角色名称
- `permission_ids`
  权限 ID 列表
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 保存角色主体和角色绑定的权限集合

### `permissions`

对应模型：`PermissionDoc`

- `perm_id`
  权限业务 ID
- `code`
  权限码，例如 `requirements:read`
- `name`
  权限名称
- `description`
  权限描述
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 保存最小权限单元

### `navigation_pages`

对应模型：`NavigationPageDoc`

- `view`
  页面视图标识
- `label`
  页面名称
- `permission`
  页面访问权限码
- `description`
  页面说明
- `order`
  页面排序
- `is_active`
  是否启用
- `is_deleted`
  是否逻辑删除
- `created_at`
  创建时间
- `updated_at`
  更新时间

用途：

- 保存导航定义与导航访问控制元数据

## Attachments 相关表

### `attachments`

对应模型：`AttachmentDoc`

- `file_id`
  文件业务 ID
- `original_filename`
  原始文件名
- `bucket`
  MinIO bucket 名称
- `object_name`
  对象存储中的文件名
- `size`
  文件大小
- `content_type`
  MIME 类型
- `uploaded_by`
  上传人
- `uploaded_at`
  上传时间
- `is_deleted`
  逻辑删除
- `deleted_at`
  删除时间

用途：

- 保存业务附件的元数据，不直接保存文件二进制

## 如何使用这篇文档

- 想查某个 collection 是做什么的：先按模块找表名
- 想查某个字段是否是业务主键、状态字段或软删除字段：直接看字段说明
- 想进一步看行为逻辑：再跳转到对应模块页或 service / application 实现
