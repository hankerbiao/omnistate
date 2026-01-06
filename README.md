# Workflow State Machine

配置驱动的工作流状态机系统，基于 Python、SQLModel 和 PostgreSQL。

## 特性

- **配置驱动**：工作流规则通过 JSON 配置定义，无需硬代码
- **有限状态机 (FSM)**：严格的状态转换控制
- **异步支持**：基于 SQLAlchemy AsyncSession
- **审计追踪**：完整的流转日志记录

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
```

服务运行在 `http://localhost:8000`，API 文档：`http://localhost:8000/docs`

## 项目结构

```
├── api/                # FastAPI 路由层
│   ├── deps.py         # 依赖注入
│   ├── main.py         # 路由汇总
│   ├── routes/         # API 端点
│   └── schemas/        # Pydantic 模型
├── configs/            # 配置文件
│   └── workflow_initial_data.json
├── db/
│   └── relational.py   # 数据库初始化
├── models/             # SQLModel 数据模型
│   ├── system.py       # 系统配置表
│   └── business.py     # 业务实体表
├── services/           # 业务逻辑层
│   ├── exceptions.py   # 自定义异常
│   └── workflow_service.py
└── main.py             # 应用入口
```

## 数据模型

### 系统配置表
| 模型 | 说明 |
|------|------|
| `SysWorkType` | 事项类型（REQUIREMENT, TEST_CASE） |
| `SysWorkflowState` | 流程状态（DRAFT, PENDING_AUDIT 等） |
| `SysWorkflowConfig` | 流转规则配置 |

### 业务实体表
| 模型 | 说明 |
|------|------|
| `BusWorkItem` | 业务事项（带状态） |
| `BusFlowLog` | 流转审计日志 |

## 工作流配置示例

编辑 `configs/workflow_initial_data.json`：

```json
{
  "work_types": [
    ["REQUIREMENT", "需求"],
    ["TEST_CASE", "测试用例"]
  ],
  "workflow_configs": [
    {
      "type_code": "REQUIREMENT",
      "from_state": "DRAFT",
      "action": "SUBMIT",
      "to_state": "PENDING_AUDIT",
      "target_owner_strategy": "TO_SPECIFIC_USER",
      "required_fields": ["priority", "target_owner_id"]
    }
  ]
}
```

### Owner Strategy

| 策略 | 说明 |
|------|------|
| `KEEP` | 保持当前处理人 |
| `TO_CREATOR` | 流转给创建者 |
| `TO_SPECIFIC_USER` | 使用 `target_owner_id` 指定处理人 |

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/work-items/types` | 获取事项类型列表 |
| GET | `/api/v1/work-items/states` | 获取流程状态列表 |
| POST | `/api/v1/work-items` | 创建业务事项 |
| GET | `/api/v1/work-items` | 查询事项列表 |
| GET | `/api/v1/work-items/{id}` | 获取事项详情 |
| POST | `/api/v1/work-items/{id}/transition` | 执行状态流转 |
| POST | `/api/v1/work-items/{id}/reassign` | 改派任务 |
| DELETE | `/api/v1/work-items/{id}` | 删除事项 |
| GET | `/api/v1/work-items/{id}/logs` | 获取流转日志 |
| GET | `/api/v1/work-items/{id}/transitions` | 获取可用流转动作 |

## 状态流转示例

```
需求流程:
DRAFT -> SUBMIT -> PENDING_AUDIT -> APPROVE -> DONE
                        |
                        -> REJECT -> DRAFT

测试用例流程:
DRAFT -> ASSIGN -> DEVELOPING -> FINISH_DEVELOP -> PENDING_REVIEW
                                                    |
                                     APPROVE -> DONE
                                     REJECT -> DEVELOPING
```