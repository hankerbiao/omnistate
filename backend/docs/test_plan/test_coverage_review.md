# DML V4 后端测试覆盖度评审报告

> 评审日期: 2026-06-16  
> 总测试函数数: 197（单元测试 147 + 集成测试 50）  
> 测试文件数: 43（单元测试 34 + 集成测试 11）  
> 跳过测试数: 11（集成测试，因字段命名不一致问题）

---

## 1. 覆盖度总览

| 模块 | 测试文件数 | 测试函数数 | 估算覆盖度 | 风险等级 |
|------|-----------|-----------|-----------|---------|
| **test_specs**（需求/用例/目录/评论） | 21 | ~140 | **~70%** | 低 |
| **auth**（认证/授权/用户/角色） | 4 | 45 | **~50%** | 中 |
| **workflow**（工作流引擎） | 7 | ~40 | **~45%** | 中 |
| **execution**（执行调度/代理/结果） | 4 | 14 | **~15%** | **高** |
| **attachments**（附件上传/下载） | (1共享) | ~4 | **~15%** | **高** |
| **shared**（共享基础设施） | 3 | 7 | **~5%** | **高** |
| 架构约束测试 | 5 | 36 | 元测试 | - |
| **execution_plan**（执行计划） | 0 | 0 | **0%** | **严重** |
| **failure_analysis**（失败分析） | 0 | 0 | **0%** | **严重** |
| **search**（全局搜索） | 0 | 0 | **0%** | **严重** |
| **ai_analysis**（AI 分析） | 0 | 0 | **0%** | **严重** |
| **system_config**（系统配置） | 0 | 0 | **0%** | **严重** |
| **test_case_collection**（用例集） | 0 | 0 | **0%** | **严重** |
| **redis**（Redis 管理） | 0 | 0 | **0%** | **严重** |
| **整体后端** | 43 | 197 | **~25-30%** | - |

---

## 2. 各模块详细评审

### 2.1 test_specs 模块（覆盖度最佳）

**文件路径**: `app/modules/test_specs/`  
**覆盖度**: ~70% — 全模块最佳

**已覆盖的内容**:
| 测试文件 | 测试函数数 | 覆盖内容 |
|----------|-----------|---------|
| `test_requirement_service.py` | 12 | 安全字段更新、负责人分配、删除、空列表、生成 ID |
| `test_test_case_service.py` | 16 | 安全字段、负责人分配、移入需求、删除、自动化关联 |
| `test_catalog_service.py` | 21 | 静态方法、Lab 验证、目录路径注册/调整、面包屑、树结构 |
| `test_lab_service.py` | 11 | 分段规范化、路径构建、Lab 增删改查、停用 |
| `test_comment_service.py` | 24 | Schema 校验、CRUD 全生命周期 — 最完善的测试 |
| `test_change_log_service.py` | 10 | 快照、追加、列表查询 |
| `test_automation_test_case_service.py` | 22 | 创建/更新、payload 提取、报告元数据、关联 |
| `test_field_diff.py` | 6 | 字段差异比较（修改/创建/标签/步骤） |
| `test_case_step_validator.py` | 6 | 步骤校验（空/重复/必填/数量限制） |
| 集成测试（5 文件） | 35 | API 级别 CRUD、分页、权限、自动化链接、目录 |

**未覆盖的内容**:
- `_workflow_status_support.py` — 状态丰富化逻辑
- `case_metadata_query.py` — 元数据查询
- `commands.py` — 命令数据类
- `query_services.py` — 查询服务
- `workflow_gateway_adapter.py` — 工作流网关适配器
- `ports.py` — 端口抽象定义

---

### 2.2 auth 模块（中等覆盖度）

**文件路径**: `app/modules/auth/`  
**覆盖度**: ~50%

**已覆盖的内容**:
| 测试文件 | 测试函数数 | 覆盖内容 |
|----------|-----------|---------|
| `test_login.py` | 8 | 登录成功/失败、获取用户信息、权限、改密码 |
| `test_user_crud.py` | 8 | 用户创建（admin/非admin）、列表、筛选、详情、更新 |
| `test_roles_permissions.py` | 4 | 角色/权限列表、创建、权限更新 |
| `test_extended.py` | 25 | 导航 CRUD、角色详情/分页/不存在、权限 CRUD、未认证访问 |

**未覆盖的内容**:
- `user_service.py` — 无直接单元测试（仅通过集成测试间接覆盖）
- `role_service.py` — 同上
- `permission_service.py` — 同上
- `navigation_access_service.py` — 零覆盖
- `navigation_page_service.py` — 仅集成测试
- `support.py` — 零覆盖
- `app/shared/auth/jwt_auth.py` — JWT 解码/验证/角色检查 — **零覆盖**（安全关键）
- `app/shared/auth/password.py` — 密码哈希/验证 — **零覆盖**（安全关键）
- 边界测试缺失: 重复用户、无效角色、已删除用户登录、Token 过期

---

### 2.3 workflow 模块（中等偏低覆盖度）

**文件路径**: `app/modules/workflow/`  
**覆盖度**: ~45%

**已覆盖的内容**:
| 测试文件 | 测试函数数 | 覆盖内容 |
|----------|-----------|---------|
| `test_workflow_policies.py` | ~8 | can_transition 8 种场景、can_reassign、can_delete |
| `test_workflow_command_service.py` | ~4 | Hook 调用验证（transition/delete 的前后钩子） |
| `test_workflow_query_service.py` | ~4 | 基于角色的流转过滤 |
| 集成测试（5 文件） | ~30 | 需求/用例全生命周期、权限、排序、搜索、删除 |

**未覆盖的内容**:
- `mutation_service.py`（`WorkflowMutationService`） — handle_transition、delete_item **零覆盖**（核心状态机逻辑）
- `rules.py` — 域规则 **零覆盖**
- `status_query.py` — 状态查询 **零覆盖**
- `common.py` — 跨模块辅助方法 **零覆盖**
- `commands.py` — 命令数据类 **零覆盖**
- 异常路径: 工作项不存在、无效 action、并发流转

---

### 2.4 execution 模块（覆盖度不足）

**文件路径**: `app/modules/execution/`  
**覆盖度**: ~15% — **高风险**

**已覆盖的内容**:
| 测试文件 | 测试函数数 | 覆盖内容 |
|----------|-----------|---------|
| `test_execution_log.py` | 5 | 执行日志上下文、JSON 格式、debug 跳过 |
| `test_execution_biz_logs_api.py` | 2 | 业务日志 limit 校验 |
| `test_execution_task_attachments.py` | 6 | 调度请求模型、附件丰富化、MinIO 优雅降级 |
| `test_agent_service.py` | 1 | 代理运行时状态解析 |

**未覆盖的内容**（核心逻辑全部零覆盖）:
- `task_command_service.py` — 任务创建/更新核心逻辑
- `task_dispatch_service.py` — 任务分发逻辑
- `task_dispatch_coordinator.py` — 分发协调
- `task_case_coordinator.py` — 用例协调
- `task_query_service.py` — 任务查询
- `task_serializer.py` — 任务序列化
- `case_resolver.py` — 用例解析
- `event_ingest_service.py` — 事件消费
- `kafka_handlers.py` — Kafka 处理器
- `progress_coordinator.py` — 进度计算
- `worker_presence.py` — 代理心跳
- `service/task_dispatcher.py` — RabbitMQ 分发
- `service/task_scheduler.py` — 调度器
- `domain/status_rules.py` — 状态规则

---

### 2.5 attachments 模块（覆盖度严重不足）

**文件路径**: `app/modules/attachments/`  
**覆盖度**: ~15%

**已覆盖**: 仅 `enrich_for_dispatch()` 一个方法（通过 execution 测试间接覆盖）  
**未覆盖**: create/get/delete/list 全部 API 路由、MinIO 上传/下载、文件类型/大小校验

---

### 2.6 shared 共享基础设施（覆盖度严重不足）

**覆盖度**: ~5%

| 组件 | 测试数 | 状态 |
|------|--------|------|
| `context.py` | 2 | 基本覆盖 |
| `middleware.py` | 2 | 基本覆盖 |
| `api/errors/handlers.py` | 3 | 基本覆盖 |
| `auth/jwt_auth.py` | 0 | **安全关键 — 零覆盖** |
| `auth/password.py` | 0 | **安全关键 — 零覆盖** |
| `kafka/*` | 0 | **零覆盖** |
| `rabbitmq/*` | 0 | **零覆盖** |
| `minio/*` | 0 | **零覆盖** |
| `config/settings.py` | 0 | **零覆盖** |
| `infrastructure/*` | 0 | **零覆盖** |

---

### 2.7 零覆盖模块（7 个）

| 模块 | API 路由数 | 核心服务 | 风险说明 |
|------|-----------|---------|---------|
| **execution_plan** | 25+ | 计划/项管理、手动结果、调度、归档 | 执行计划核心功能完全无保障 |
| **failure_analysis** | 1 | 仪表盘聚合、模式分类 | 数据分析模块无测试 |
| **search** | 1 | 跨实体搜索 | 搜索功能无测试 |
| **ai_analysis** | 1 | LLM 集合分析 | AI 集成无测试 |
| **system_config** | 8 | 配置 CRUD、缓存、AI 连接 | 配置管理无测试 |
| **test_case_collection** | 6 | 集合 CRUD、用例增删 | 用例集无测试 |
| **redis** | 5 | Redis 键管理 | Redis 管理无测试 |

---

## 3. 集成测试问题

### 3.1 跳过的测试
11 个集成测试被跳过，原因是 `item_id` vs `req_id` 字段命名不一致的 bug，影响测试可信度。

### 3.2 断言精确性
部分集成测试接受多个状态码（如 `"400 or 403 or 404"`），表明断言不够精确，可能掩盖实际错误。

### 3.3 环境依赖
集成测试依赖运行中的 MongoDB，限制 CI 自动化执行。

---

## 4. 现有测试的优势

1. **test_specs 模块** — 21 个测试文件，覆盖全面，是测试编写的标杆
2. **CommentService** — 24 个测试覆盖全生命周期，可作为服务层测试范例
3. **架构边界测试** — 5 个元测试文件，有效防止层间依赖违规
4. **域策略测试** — workflow 的 can_transition 8 种场景覆盖全面

---

## 5. 改进建议（按优先级排序）

### P0 - 立即行动
| 编号 | 建议 | 原因 |
|------|------|------|
| 1 | 修复 `item_id` vs `req_id` 字段命名不一致的 bug，恢复 11 个跳过的集成测试 | 这些测试原本应覆盖核心业务路径 |
| 2 | 为 `shared/auth/jwt_auth.py` 添加单元测试（Token 解码、过期、签名校验） | 安全关键代码 |
| 3 | 为 `shared/auth/password.py` 添加单元测试（哈希、验证） | 安全关键代码 |

### P1 - 重要
| 编号 | 建议 | 原因 |
|------|------|------|
| 4 | 为 `workflow/mutation_service.py` 添加核心状态流转测试 | 工作流引擎的核心逻辑 |
| 5 | 为 `execution/task_command_service.py` 添加任务生命周期测试 | 执行调度的核心逻辑 |
| 6 | 为 `execution_plan` 模块编写基本 CRUD 测试 | 零覆盖模块，业务价值高 |
| 7 | 添加 `system_config` 模块的配置 CRUD 和验证测试 | 配置管理直接影响系统行为 |
| 8 | 为 `shared/kafka/*` 添加生产者/消费者测试 | 消息基础设施无任何保障 |

### P2 - 逐步完善
| 编号 | 建议 | 原因 |
|------|------|------|
| 9 | 为 `search`、`ai_analysis`、`test_case_collection` 添加基本测试 | 新功能回归保障 |
| 10 | 添加 `attachments` 模块的 MinIO 上传/下载测试 | 文件功能无测试 |
| 11 | 提高集成测试断言精确度 | 避免掩盖错误 |
| 12 | 添加 CI 集成的 MongoDB 容器化支持 | 自动化执行集成测试 |

---

## 6. 附录：测试文件清单

### 单元测试（`tests/unit/`）

```
tests/unit/
├── conftest.py                              # 共享 Fixture
├── test_exception_handlers.py               # 3 tests
├── test_middleware.py                       # 2 tests
├── test_context.py                          # 2 tests
├── test_module_boundaries.py                # 23 tests（架构）
├── test_redundancy_governance.py            # 5 tests（架构）
├── test_startup_composition.py              # 2 tests（架构）
├── test_file_sizes.py                       # 2 tests（架构）
├── test_status_projection_boundaries.py     # 4 tests（架构）
├── workflow/
│   ├── test_workflow_command_service.py
│   ├── test_workflow_query_service.py
│   └── test_workflow_policies.py
├── test_specs/
│   ├── test_requirement_service.py
│   ├── test_test_case_service.py
│   ├── test_catalog_service.py
│   ├── test_lab_service.py
│   ├── test_comment_service.py
│   ├── test_change_log_service.py
│   ├── test_automation_test_case_service.py
│   ├── test_field_diff.py
│   ├── test_case_step_validator.py
│   ├── test_requirement_command_policy.py
│   ├── test_requirement_serialization.py
│   ├── test_workflow_command_support.py
│   ├── test_service_support.py
│   ├── test_workflow_edit_policies.py
│   ├── test_status_projection_behavior.py
│   ├── test_status_projection_migration.py
│   └── test_test_case_create_initial_state.py
├── execution/
│   ├── test_agent_service.py
│   ├── test_execution_biz_logs_api.py
│   ├── test_execution_log.py
│   └── test_execution_task_attachments.py
└── terminal/
    └── test_terminal_module.py
```

### 集成测试（`tests/integration/`）

```
tests/integration/
├── conftest.py                              # Fixture + 数据清理
├── utils/
│   ├── client.py                            # 测试 HTTP 客户端
│   └── helpers.py                           # 测试辅助函数
├── auth/
│   ├── test_login.py
│   ├── test_user_crud.py
│   ├── test_roles_permissions.py
│   └── test_extended.py
├── workflow/
│   ├── test_requirement_lifecycle.py
│   ├── test_testcase_lifecycle.py
│   ├── test_requirement_case_link.py
│   ├── test_workflow_extended.py
│   └── test_permission_enforcement.py
└── test_specs/
    ├── test_requirement_crud.py
    ├── test_case_crud.py
    ├── test_case_automation_link.py
    ├── test_case_catalog_fields.py
    └── test_catalog_labs_api.py
```
