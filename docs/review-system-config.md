# 系统配置模块评审报告

## 一、整体架构

系统有两个配置源：

1. **config.yaml**（静态文件）— 由 `app/shared/config/settings.py` 加载，通过 `get_settings()`（`@lru_cache` 单例）访问
2. **MongoDB `system_configs` 集合**（动态 DB）— 由 `app/modules/system_config/` 模块管理，通过 `ConfigService` 提供 CRUD + 缓存

## 二、当前状态总览

| # | 问题 | 状态 | 说明 |
|---|------|------|------|
| 1 | `_apply_defaults` 中 repo_url / branch fallback 顺序不一致 | **已修复** | 统一为"系统配置优先，config.yaml 兜底" |
| 2 | `_get_system_config_sync` 每次创建新 MongoDB 连接 | **已修复** | 改用 `asyncio.run_coroutine_threadsafe` 复用 Beanie 连接池 |
| 3 | `_remove_from_yaml` 删除 yaml 后重启前仍读到旧值 | **待修复** | `get_settings()` 的 `@lru_cache` 导致缓存不一致 |
| 4 | `init_default_configs` 硬编码覆盖 config.yaml | **已修复** | 已有 `_try_read_yaml_value` 优先读取 config.yaml |
| 5 | AI / execution 配置读取路径不一致 | **设计如此** | AI 配置读 MongoDB（支持热更新），execution 读 config.yaml（需重启） |

---

## 三、已修复的问题（文档与代码同步确认）

### ~~问题 1：`_apply_defaults` fallback 顺序不一致~~

**位置**: `app/modules/execution/application/task_command_helpers.py:350-380`

实际代码中，`repo_url` 和 `branch` 均已统一为 **系统配置（MongoDB）优先，config.yaml 兜底**：

```python
# repo_url/branch：以系统配置（MongoDB）为准，config.yaml 作为最终兜底
if command.repo_url is None:
    mongo_repo_url = _get_system_config_sync("execution.default_repo_url")
    command.repo_url = mongo_repo_url or execution_cfg.default_repo_url
if command.branch is None:
    mongo_branch = _get_system_config_sync("execution.default_branch")
    command.branch = mongo_branch or execution_cfg.default_branch
```

两者 fallback 逻辑一致。无需额外修改。

### ~~问题 2：`_get_system_config_sync` 每次创建新 MongoDB 连接~~

**位置**: `app/modules/execution/application/task_command_helpers.py:170-203`

实际代码已改用 Beanie 连接池（通过 `asyncio.run_coroutine_threadsafe`）：

```python
def _get_system_config_sync(key: str) -> str | None:
    """同步读取系统配置值（用于非 async 上下文）。
    使用已有的 Beanie 连接（通过 asyncio.run_coroutine_threadsafe），
    避免每次创建新的 MongoDB 连接。
    """
    try:
        import asyncio
        from app.modules.system_config.repository.models import SystemConfigDoc
        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                _async_get_config(key), loop
            )
            return future.result(timeout=5)
        else:
            return asyncio.run(_async_get_config(key))
    except Exception as e:
        log.warning(f"Failed to read system config '{key}': {e}")
        return None
```

**剩余问题**：异常捕获范围仍偏宽（`Exception`），但日志已从静默吞掉改为 `log.warning`，可接受。

### ~~问题 4：`init_default_configs` 硬编码覆盖 config.yaml~~

**位置**: `app/modules/system_config/service/config_service.py:303-323`

实际代码已有 `_try_read_yaml_value` 逻辑，优先从 config.yaml 读取实际值：

```python
async def init_default_configs() -> None:
    for config in ConfigService.DEFAULT_CONFIGS:
        existing = await SystemConfigDoc.find_one(...)
        if not existing:
            # 从 config.yaml 读取实际值
            yaml_value = ConfigService._try_read_yaml_value(config["config_key"])
            if yaml_value is not None:
                config["config_value"] = yaml_value
            doc = SystemConfigDoc(**config)
            await doc.insert()
```

`_try_read_yaml_value` 通过 `get_settings()` 读取已加载的配置值，确保 MongoDB 初始值与 config.yaml 一致。

---

## 四、待修复的问题

### 问题 3：`_remove_from_yaml` 删除 yaml 后 `get_settings()` 缓存仍为旧值

**位置**:
- `app/modules/system_config/service/config_service.py:110-139` — `_remove_from_yaml`
- `app/shared/config/settings.py:257-265` — `get_settings()` 的 `@lru_cache`

**现象**：
1. 用户通过 API 保存配置（如 `execution.default_branch`）
2. `set_config()` 调用 `_remove_from_yaml()` 从 config.yaml 删除该键
3. 但 `get_settings()` 使用 `@lru_cache`，在进程重启前返回的仍是缓存中的旧值
4. 对于 `needs_restart=True` 的配置项，用户期望重启后生效 — 但旧值已被删除，新值（MongoDB）因重启前代码不读 MongoDB 而不会被使用

**影响分析**：
- `needs_restart=True` 的配置项（`app.debug`、`execution.default_repo_url`、`jwt.expire_minutes` 等）受此影响
- `needs_restart=False` 的配置项不受影响，因为代码会主动读取 MongoDB

**推荐方案**：

方案 A（推荐）：移除 `_remove_from_yaml`，改为在 `get_settings()` 中增加运行时配置覆盖层。

```python
# app/shared/config/settings.py
from app.modules.system_config.repository.models import SystemConfigDoc

@lru_cache
def get_settings() -> Settings:
    config_data = load_yaml_config()
    settings = Settings(**config_data)
    return settings

# 新增：运行时覆盖层，使 get_settings() 能感知系统配置
# 调用方使用 get_effective_settings() 替代 get_settings()
_OVERRIDES: dict[str, Any] = {}

def apply_override(key: str, value: Any) -> None:
    """应用运行时配置覆盖（由 ConfigService.set_config 调用）。"""
    _OVERRIDES[key] = value

def get_effective_settings() -> Settings:
    """获取合并了运行时覆盖的配置。"""
    settings = get_settings()
    for key, value in _OVERRIDES.items():
        parts = key.split(".")
        if len(parts) == 2:
            section = getattr(settings, parts[0], None)
            if section:
                setattr(section, parts[1], value)
    return settings
```

方案 B（简单）：移除 `_remove_from_yaml`，用户通过 API 保存配置后，读取系统配置的代码已优先读 MongoDB，yaml 中的旧值不会影响业务逻辑。重启后 yaml 中的值会通过 `init_default_configs` 同步到 MongoDB。

---

## 五、设计如此（无需修改）

### 问题 5：AI / execution 配置读取路径不一致

| 配置域 | 读取来源 | 原因 |
|--------|----------|------|
| AI 配置 (`ai.*`) | MongoDB（`ConfigService.get_config`） | 需热更新，用户可在 UI 修改后立即生效 |
| 执行配置 (`execution.*`) | config.yaml（`get_settings().execution`） | 涉及任务下发，需重启确保一致性 |

这是有意设计，并非不一致。两类配置的更新频率和影响范围不同，采用不同的读取策略是合理的。

---

## 六、其他观察

### 6.1 `_try_read_yaml_value` 依赖 `get_settings()` 的 `@lru_cache`

**位置**: `app/modules/system_config/service/config_service.py:286-301`

```python
@staticmethod
def _try_read_yaml_value(config_key: str) -> Optional[str]:
    from app.shared.config.settings import get_settings
    settings = get_settings()
    parts = config_key.split(".")
    if len(parts) == 2:
        section, key = parts
        obj = getattr(settings, section, None)
        if obj:
            value = getattr(obj, key, None)
            if value is not None:
                return str(value)
    return None
```

此函数在 `init_default_configs` 中被调用，用于在首次部署时将 config.yaml 的值同步到 MongoDB。由于 `get_settings()` 有 `@lru_cache`，config.yaml 修改后需重启才能反映变更 — 但这在首次部署场景下不是问题（config.yaml 在启动时已是最新）。

### 6.2 `ConfigCache` 的 TTL 是 5 分钟

**位置**: `app/modules/system_config/service/config_service.py:35`

```python
_cache_ttl: float = 300  # 5分钟缓存
```

`get_config` 读 MongoDB 后缓存 5 分钟。如果其他进程直接修改了 MongoDB，配置变更最多延迟 5 分钟生效。可通过调用 `reload_config(key)` 立即清除缓存。
