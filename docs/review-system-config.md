# 系统配置模块评审报告

## 一、整体架构

系统有两个配置源：

1. **config.yaml**（静态文件）— 由 `app/shared/config/settings.py` 加载，通过 `get_settings()` 全局单例访问
2. **MongoDB `system_configs` 集合**（动态 DB）— 由 `app/modules/system_config/` 模块管理，通过 `ConfigService` 提供 CRUD

## 二、发现的问题

### 问题 1：`_apply_defaults` 中存在 config.yaml 优先于系统配置的 fallback 逻辑

**位置**: `app/modules/execution/application/task_command_helpers.py:331-359`

```python
def _apply_defaults(command: DispatchExecutionTaskCommand) -> None:
    execution_cfg = get_settings().execution  # 从 config.yaml 读取
    ...
    # repo_url: config.yaml 优先于系统配置
    if command.repo_url is None:
        command.repo_url = execution_cfg.default_repo_url or _get_system_config_sync("execution.default_repo_url")

    # branch: 系统配置优先于 config.yaml（不一致！）
    if command.branch is None:
        mongo_branch = _get_system_config_sync("execution.default_branch")
        command.branch = mongo_branch or execution_cfg.default_branch
```

**问题**: `repo_url` 和 `branch` 的 fallback 顺序不一致。且两者都没有以系统配置（MongoDB）为准，而是以 config.yaml 为准或互相兜底。

### 问题 2：`_get_system_config_sync` 每次创建新 MongoDB 连接

**位置**: `app/modules/execution/application/task_command_helpers.py:170-184`

```python
def _get_system_config_sync(key: str) -> str | None:
    try:
        from pymongo import MongoClient
        from app.shared.config import get_settings
        settings = get_settings()
        client = MongoClient(settings.mongodb.uri)
        db = client[settings.mongodb.db_name]
        doc = db["system_configs"].find_one({"config_key": key})
        client.close()
        if doc and doc.get("config_value"):
            return str(doc["config_value"])
    except Exception:
        pass
    return None
```

**问题**:
- 每次调用都创建/销毁 MongoDB 连接，性能差
- 所有异常都被静默吞噬（`except Exception: pass`），任何 MongoDB 错误都会导致静默回退到 config.yaml

### 问题 3：`_remove_from_yaml` 在保存系统配置时清理 yaml，但重启前 config.yaml 仍被读取

**位置**: `app/modules/system_config/service/config_service.py:111-139`

当用户通过 API 保存配置时，`set_config()` 会调用 `_remove_from_yaml()` 从 config.yaml 中删除该键。但 `get_settings()` 使用的是 `@lru_cache`，在服务重启前 config.yaml 的旧值仍然有效。对于 `needs_restart=True` 的配置项，重启前新旧值都不会被使用。

### 问题 4：`init_default_configs` 使用硬编码默认值，可能覆盖 config.yaml 的实际值

**位置**: `app/modules/system_config/service/config_service.py:286-293`

```python
@staticmethod
async def init_default_configs() -> None:
    for config in ConfigService.DEFAULT_CONFIGS:
        existing = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == config["config_key"])
        if not existing:
            doc = SystemConfigDoc(**config)
            await doc.insert()
```

首次部署时，`DEFAULT_CONFIGS` 中的硬编码默认值会被写入 MongoDB。如果 config.yaml 中有不同的值，系统配置（MongoDB）和 config.yaml 会不一致。

例如:
- config.yaml: `execution.default_branch: main`
- MongoDB: `execution.default_branch: master`（DEFAULT_CONFIGS 硬编码）
- 代码读取: `get_settings().execution.default_branch` → `main`（config.yaml 优先）
- 用户在界面上看到: `master`（从 MongoDB 读取）

### 问题 5：AI 配置读取路径不一致

- `ai_service.py` 通过 `ConfigService.get_ai_config()` 和 `ConfigService.get_config("ai.max_cases")` 读取 MongoDB
- 但 `execution` 模块通过 `get_settings().execution` 读取 config.yaml

AI 配置只读 MongoDB（不读 config.yaml），而执行配置会 fallback 到 config.yaml。不同模块读取配置的策略不一致。

## 三、推荐修改方案

### 修改 1：统一 `_apply_defaults` 以系统配置（MongoDB）为准

将 `repo_url` 和 `branch` 的 fallback 改为：**系统配置优先，config.yaml 作为最终兜底**（即 MongoDB 有值就用 MongoDB，没有再用 config.yaml）。

并且统一两者的顺序：

```python
# repo_url: 系统配置优先
mongo_repo_url = _get_system_config_sync("execution.default_repo_url")
command.repo_url = command.repo_url or mongo_repo_url or execution_cfg.default_repo_url

# branch: 系统配置优先
mongo_branch = _get_system_config_sync("execution.default_branch")
command.branch = command.branch or mongo_branch or execution_cfg.default_branch
```

### 修改 2：修复 `_get_system_config_sync` 的连接管理和异常处理

使用 Beanie（已有的异步 ORM）代替每次创建 pymongo 连接。或者使用连接池。

### 修改 3：`init_default_configs` 读取 config.yaml 的实际值作为默认值

在 `init_default_configs` 中，对于 `YAML_SECTIONS` 中的配置项，先从 `get_settings()` 读取当前值作为默认值，而不是使用硬编码：

```python
for config in ConfigService.DEFAULT_CONFIGS:
    existing = await SystemConfigDoc.find_one(...)
    if not existing:
        # 尝试从 config.yaml 读取当前值
        yaml_value = _try_read_from_yaml(config["config_key"])
        if yaml_value is not None:
            config["config_value"] = yaml_value
        doc = SystemConfigDoc(**config)
        await doc.insert()
```

### 修改 4：移除静默的异常捕获

在 `_get_system_config_sync` 中，改为只捕获预期的异常（如连接超时），而不是吞掉所有异常。

### 修改 5：添加系统配置 API 的初始化端点

提供一个 API 端点，允许用户在部署后手动触发从 config.yaml 同步到系统配置，而不是在启动时自动写入默认值。
