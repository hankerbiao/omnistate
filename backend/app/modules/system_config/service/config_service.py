"""
系统配置服务层。

Configuration source rules:
- BOOTSTRAP configuration only comes from YAML/environment variables.
- RUNTIME configuration only comes from MongoDB system_configs.
- Missing or invalid runtime configuration is a startup error.
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Any, Optional

from app.modules.system_config.repository.models import SystemConfigDoc, SystemConfigHistoryDoc
from app.modules.system_config.constants.ai_analysis import AI_ANALYSIS_PROMPT_CONFIGS
from app.modules.system_config.schemas import AIConfig
from app.modules.system_config.service.config_catalog import RUNTIME_CONFIG_DESCRIPTIONS
from app.shared.config import RuntimeSettings, get_environment, get_settings, install_runtime_settings
from app.shared.core.logger import log


def _flatten_config(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for name, value in data.items():
        key = f"{prefix}.{name}" if prefix else name
        if isinstance(value, dict):
            flattened.update(_flatten_config(value, key))
        else:
            flattened[key] = value
    return flattened


def _unflatten_config(data: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for key, value in data.items():
        cursor = nested
        parts = key.split(".")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = value
    return nested


def _config_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, (dict, list)):
        return "json"
    return "string"


def _serialize_value(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError("invalid boolean")


def _runtime_config_templates() -> list[dict[str, Any]]:
    defaults = _flatten_config(RuntimeSettings().model_dump())
    if set(defaults) != set(RUNTIME_CONFIG_DESCRIPTIONS):
        missing = sorted(set(defaults) - set(RUNTIME_CONFIG_DESCRIPTIONS))
        stale = sorted(set(RUNTIME_CONFIG_DESCRIPTIONS) - set(defaults))
        raise RuntimeError(
            f"运行配置中文描述目录不完整，缺少={missing}，多余={stale}"
        )
    return [
        {
            "config_key": key,
            "config_value": _serialize_value(value),
            "config_type": _config_type(value),
            "category": key.split(".", 1)[0],
            "description": RUNTIME_CONFIG_DESCRIPTIONS[key],
            "needs_restart": True,
        }
        for key, value in defaults.items()
    ]


class ConfigCache:
    """配置缓存管理器"""

    _cache: dict[str, tuple[Any, float]] = {}
    _lock = asyncio.Lock()
    _ttl: float = 300

    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        async with cls._lock:
            if key in cls._cache:
                value, ts = cls._cache[key]
                if time.time() - ts < cls._ttl:
                    return value
                del cls._cache[key]
            return None

    @classmethod
    async def set(cls, key: str, value: Any) -> None:
        async with cls._lock:
            cls._cache[key] = (value, time.time())

    @classmethod
    async def invalidate(cls, key: Optional[str] = None) -> None:
        async with cls._lock:
            if key is None:
                cls._cache.clear()
            elif key in cls._cache:
                del cls._cache[key]


class ConfigService:
    """MongoDB 运行时配置服务。"""

    AI_CONFIGS: list[dict[str, Any]] = [
        {"config_key": "ai.base_url", "config_value": "http://localhost:11434/v1", "config_type": "string", "category": "ai", "description": "LLM API基础URL"},
        {"config_key": "ai.model", "config_value": "qwen2.5:latest", "config_type": "string", "category": "ai", "description": "LLM模型名称"},
        {"config_key": "ai.api_key", "config_value": "", "config_type": "string", "category": "ai", "description": "API密钥（如需要）"},
        {"config_key": "ai.enabled", "config_value": "true", "config_type": "boolean", "category": "ai", "description": "是否启用AI分析"},
        {"config_key": "ai.temperature", "config_value": "0.7", "config_type": "float", "category": "ai", "description": "生成温度参数"},
        {"config_key": "ai.max_tokens", "config_value": "2048", "config_type": "integer", "category": "ai", "description": "最大生成token数"},
        {"config_key": "ai.timeout", "config_value": "60", "config_type": "integer", "category": "ai", "description": "请求超时时间(秒)"},
        {"config_key": "ai.max_cases", "config_value": "100", "config_type": "integer", "category": "ai", "description": "单次AI分析最大用例数"},
        {"config_key": "ai.embedding_base_url", "config_value": "http://10.8.136.35:8002/v1", "config_type": "string", "category": "ai", "description": "Embedding API 基础URL"},
        {"config_key": "ai.embedding_model", "config_value": "qwen3-vl-embedding", "config_type": "string", "category": "ai", "description": "Embedding 模型名称"},
        *AI_ANALYSIS_PROMPT_CONFIGS,
    ]

    RUNTIME_CONFIGS: list[dict[str, Any]] = _runtime_config_templates()
    DEFAULT_CONFIGS: list[dict[str, Any]] = AI_CONFIGS + RUNTIME_CONFIGS

    _DEFAULTS_MAP: dict[str, dict[str, Any]] = {
        config["config_key"]: config for config in DEFAULT_CONFIGS
    }

    _PARSERS: dict[str, Any] = {
        "integer": int,
        "float": float,
        "boolean": _parse_boolean,
        "json": json.loads,
    }

    _AI_CONFIG_MAPPING: dict[str, str] = {
        "ai.base_url": "base_url",
        "ai.model": "model",
        "ai.api_key": "api_key",
        "ai.enabled": "enabled",
        "ai.temperature": "temperature",
        "ai.max_tokens": "max_tokens",
        "ai.timeout": "timeout",
        "ai.embedding_base_url": "embedding_base_url",
        "ai.embedding_model": "embedding_model",
    }

    @classmethod
    def _is_runtime_config_key(cls, key: str) -> bool:
        """判断配置键是否归 MongoDB 运行时配置所有。"""
        return key in cls._DEFAULTS_MAP

    @staticmethod
    def _serialize_setting(value: Any) -> str:
        return _serialize_value(value)

    @staticmethod
    async def get_config(key: str) -> Any:
        """Get a required MongoDB configuration value with a short cache."""
        if not ConfigService._is_runtime_config_key(key):
            raise ValueError(f"未知运行配置项: {key}")

        cached = await ConfigCache.get(key)
        if cached is not None:
            return cached

        doc = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == key)
        if doc is None or not doc.is_active:
            raise RuntimeError(f"运行配置缺失或未启用: {key}")

        expected_type = ConfigService._DEFAULTS_MAP[key]["config_type"]
        if doc.config_type != expected_type:
            raise RuntimeError(
                f"运行配置类型错误: {key} 应为 {expected_type}，实际为 {doc.config_type}"
            )
        value = ConfigService._parse_value_strict(doc.config_value, expected_type)
        await ConfigCache.set(key, value)
        return value

    @staticmethod
    async def get_config_by_key(config_key: str) -> Optional[SystemConfigDoc]:
        """获取单个运行时配置文档。"""
        if not ConfigService._is_runtime_config_key(config_key):
            return None
        return await SystemConfigDoc.find_one(SystemConfigDoc.config_key == config_key)

    @staticmethod
    async def get_configs(
        category: Optional[str] = None,
        active_only: bool = True,
        search: Optional[str] = None,
    ) -> tuple[list[SystemConfigDoc], int]:
        """获取运行时配置列表。"""
        query: dict[str, Any] = {"config_key": {"$in": list(ConfigService._DEFAULTS_MAP)}}
        if active_only:
            query["is_active"] = True
        if category:
            query["category"] = category
        if search:
            query["$or"] = [
                {"config_key": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        docs = await SystemConfigDoc.find(query).to_list()
        return docs, len(docs)

    @staticmethod
    async def get_categories() -> list[str]:
        """获取运行时配置分类。"""
        docs = await SystemConfigDoc.find({"config_key": {"$in": list(ConfigService._DEFAULTS_MAP)}}).to_list()
        return sorted(set(doc.category for doc in docs))

    @staticmethod
    async def get_ai_config() -> dict[str, Any]:
        """获取 AI 相关配置（用于 LLM 调用）。"""
        config = AIConfig()
        for key, field in ConfigService._AI_CONFIG_MAPPING.items():
            value = await ConfigService.get_config(key)
            if value is not None:
                setattr(config, field, value)
        return config.model_dump()

    @classmethod
    async def load_runtime_settings(cls, *, install: bool = True) -> RuntimeSettings:
        """Load and install a complete runtime snapshot from MongoDB."""
        expected = {item["config_key"]: item for item in cls.RUNTIME_CONFIGS}
        docs = await SystemConfigDoc.find(
            {
                "config_key": {"$in": list(expected)},
                "is_active": True,
            }
        ).to_list()
        by_key = {doc.config_key: doc for doc in docs}
        missing = sorted(set(expected) - set(by_key))
        if missing:
            raise RuntimeError(
                "MongoDB 运行配置不完整，缺少: " + ", ".join(missing)
            )

        invalid_types = sorted(
            key
            for key, template in expected.items()
            if by_key[key].config_type != template["config_type"]
        )
        if invalid_types:
            raise RuntimeError(
                "MongoDB 运行配置类型元数据错误: " + ", ".join(invalid_types)
            )

        parsed = {
            key: cls._parse_value_strict(
                by_key[key].config_value,
                expected[key]["config_type"],
            )
            for key in expected
        }
        runtime = RuntimeSettings.model_validate(_unflatten_config(parsed), strict=True)
        if install:
            install_runtime_settings(runtime)
        log.info(
            "Loaded {} runtime settings from MongoDB for environment {}",
            len(parsed),
            get_environment(),
        )
        return runtime

    @classmethod
    async def validate_runtime_updates(cls, updates: dict[str, str]) -> None:
        """Validate proposed restart-bound values against the complete DB snapshot."""
        runtime_updates = {
            key: value for key, value in updates.items() if key in {
                item["config_key"] for item in cls.RUNTIME_CONFIGS
            }
        }
        if not runtime_updates:
            return

        expected = {item["config_key"]: item for item in cls.RUNTIME_CONFIGS}
        docs = await SystemConfigDoc.find(
            {"config_key": {"$in": list(expected)}, "is_active": True}
        ).to_list()
        by_key = {doc.config_key: doc for doc in docs}
        missing = sorted(set(expected) - set(by_key))
        if missing:
            raise ValueError("运行配置不完整，缺少: " + ", ".join(missing))

        parsed: dict[str, Any] = {}
        for key, template in expected.items():
            value = runtime_updates.get(key, by_key[key].config_value)
            parsed[key] = cls._parse_value_strict(value, template["config_type"])
        RuntimeSettings.model_validate(_unflatten_config(parsed), strict=True)

    @classmethod
    def is_pending_restart(cls, doc: SystemConfigDoc) -> bool:
        if not doc.needs_restart:
            return False
        effective = _flatten_config(
            {
                section: getattr(get_settings(), section).model_dump()
                for section in RuntimeSettings.model_fields
            }
        )
        return _serialize_value(effective.get(doc.config_key)) != doc.config_value

    @staticmethod
    async def set_config(
        key: str,
        value: Any,
        changed_by: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> SystemConfigDoc:
        """设置运行时配置值（自动记录历史，明文存储）。"""
        if not ConfigService._is_runtime_config_key(key):
            raise ValueError(f"配置项不属于运行时配置，不能写入 MongoDB: {key}")

        doc = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == key)
        default = ConfigService._DEFAULTS_MAP[key]
        stored_value = ConfigService._serialize_setting(value)
        if doc:
            await ConfigService._save_history(
                key,
                doc.config_value,
                stored_value,
                changed_by,
                remark,
            )
            doc.config_value = stored_value
            doc.config_type = default.get("config_type", "string")
            doc.category = default.get("category", "general")
            doc.description = default.get("description")
            doc.needs_restart = default.get("needs_restart", False)
            doc.updated_at = datetime.utcnow()
            doc.updated_by = changed_by
        else:
            doc = SystemConfigDoc(
                config_key=key,
                config_value=stored_value,
                config_type=default.get("config_type", "string"),
                category=default.get("category", "general"),
                description=default.get("description"),
                needs_restart=default.get("needs_restart", False),
                updated_by=changed_by,
            )

        await (doc.save() if doc.id else doc.insert())
        await ConfigCache.invalidate(key)
        return doc

    @staticmethod
    async def batch_update(
        items: list[dict[str, str]],
        changed_by: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> int:
        """批量更新运行时配置。"""
        count = 0
        for item in items:
            key, value = item.get("config_key"), item.get("config_value")
            if key and value is not None:
                await ConfigService.set_config(key, value, changed_by, remark)
                count += 1
        return count

    @staticmethod
    async def reload_config(key: Optional[str] = None) -> None:
        """热加载配置（清除缓存）。"""
        await ConfigCache.invalidate(key)

    @staticmethod
    async def import_configs(
        values: dict[str, Any],
        *,
        changed_by: str = "config-migration",
        overwrite: bool = True,
    ) -> int:
        """Explicitly import configuration values; never called at startup."""
        imported = 0
        for key, value in values.items():
            if not ConfigService._is_runtime_config_key(key):
                raise ValueError(f"未知运行配置项: {key}")
            existing = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == key)
            if existing and not overwrite:
                continue
            await ConfigService.set_config(
                key,
                value,
                changed_by=changed_by,
                remark="从 YAML 显式迁移到 MongoDB",
            )
            imported += 1
        return imported

    @staticmethod
    async def sync_config_metadata() -> int:
        """Synchronize catalog metadata without creating or changing values."""
        missing: list[str] = []
        updated = 0
        for template in ConfigService.DEFAULT_CONFIGS:
            key = template["config_key"]
            doc = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == key)
            if doc is None:
                missing.append(key)
                continue
            doc.config_type = template.get("config_type", "string")
            doc.category = template.get("category", "general")
            doc.description = template.get("description")
            doc.needs_restart = template.get("needs_restart", False)
            await doc.save()
            updated += 1
        if missing:
            raise RuntimeError("运行配置不完整，缺少: " + ", ".join(sorted(missing)))
        return updated

    @staticmethod
    async def test_ai_connection(
        base_url: str,
        model: str,
        api_key: Optional[str] = None,
        timeout: int = 60,
    ) -> dict[str, Any]:
        """测试 AI 服务连接。"""
        start = time.time()
        try:
            import openai

            def _sync_test():
                client = openai.OpenAI(base_url=base_url, api_key=api_key or "ollama", timeout=timeout)
                return client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=10,
                )

            response = await asyncio.to_thread(_sync_test)
            return {
                "success": True,
                "model": response.model,
                "response_time_ms": int((time.time() - start) * 1000),
            }
        except Exception as exc:
            log.error("AI connection test failed: {}", exc)
            return {
                "success": False,
                "error": str(exc),
                "response_time_ms": int((time.time() - start) * 1000),
            }

    @staticmethod
    async def get_history(config_key: Optional[str] = None, limit: int = 50) -> list[SystemConfigHistoryDoc]:
        """获取运行时配置历史。"""
        query: dict[str, Any] = {"config_key": {"$in": list(ConfigService._DEFAULTS_MAP)}}
        if config_key and ConfigService._is_runtime_config_key(config_key):
            query["config_key"] = config_key
        elif config_key:
            return []
        return await SystemConfigHistoryDoc.find(query).sort("-changed_at").limit(limit).to_list()

    @staticmethod
    async def _save_history(
        config_key: str,
        old_value: Optional[str],
        new_value: Optional[str],
        changed_by: Optional[str],
        remark: Optional[str],
    ) -> None:
        await SystemConfigHistoryDoc(
            config_key=config_key,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            remark=remark,
        ).insert()

    @staticmethod
    def _parse_value(value: str, config_type: str) -> Any:
        """根据类型解析配置值。"""
        return ConfigService._parse_value_strict(value, config_type)

    @staticmethod
    def _parse_value_strict(value: str, config_type: str) -> Any:
        parser = ConfigService._PARSERS.get(config_type)
        return parser(value) if parser else value


class ConfigValidator:
    """配置验证器"""

    _RULES: dict[str, tuple[Any, str]] = {
        "ai.base_url": (
            lambda v: v.startswith(("http://", "https://")),
            "URL必须以http://或https://开头",
        ),
        "ai.temperature": (
            lambda v: 0 <= float(v) <= 2,
            "温度参数必须在0-2之间",
        ),
        "ai.max_tokens": (
            lambda v: int(v) >= 1,
            "Token数量不能小于1",
        ),
        "ai.timeout": (
            lambda v: 5 <= int(v) <= 300,
            "超时时间必须在5-300秒之间",
        ),
    }

    @staticmethod
    def validate(config_key: str, config_value: str) -> tuple[bool, str]:
        """验证配置值，返回 (是否有效, 错误信息)。"""
        if not ConfigService._is_runtime_config_key(config_key):
            return False, f"配置项不属于运行时配置，不能写入 MongoDB: {config_key}"

        template = ConfigService._DEFAULTS_MAP[config_key]
        try:
            ConfigService._parse_value_strict(config_value, template["config_type"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return False, f"配置值必须是有效的 {template['config_type']} 类型"

        rule = ConfigValidator._RULES.get(config_key)
        if not rule:
            return True, ""

        checker, error_msg = rule
        try:
            if not checker(config_value):
                return False, error_msg
        except (ValueError, TypeError):
            return False, error_msg

        if config_key == "ai.base_url":
            from urllib.parse import urlparse
            try:
                urlparse(config_value)
            except Exception:
                return False, "无效的URL格式"

        return True, ""
