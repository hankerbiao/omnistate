"""
系统配置服务层

提供配置的 CRUD、热加载、缓存和 AI 连接测试功能

配置唯一入口原则：
- 运行时可热修改的配置（ai.*, system.*）存储在 MongoDB system_configs 集合
- 需要重启生效的基础设施配置（execution.*, jwt.*, logging.*, app.*）存储在 config.yaml
- 系统配置 API 不会修改 config.yaml，避免运行时 YAML 写入导致的配置漂移
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Any, Optional

from app.modules.system_config.repository.models import SystemConfigDoc, SystemConfigHistoryDoc
from app.modules.system_config.schemas import AIConfig
from app.shared.core.logger import log


class ConfigCache:
    """配置缓存管理器"""

    _cache: dict[str, tuple[Any, float]] = {}
    _lock = asyncio.Lock()
    _ttl: float = 300  # 5分钟缓存

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
    """系统配置服务"""

    # ── 常量 ────────────────────────────────────────────────

    # 运行时可热修改的默认配置项（AI 配置）
    # 需要重启的基础设施配置（execution.*, jwt.*, logging.*, app.*）统一在 config.yaml 中管理
    DEFAULT_CONFIGS: list[dict[str, str]] = [
        {"config_key": "ai.base_url",   "config_value": "http://localhost:11434/v1", "config_type": "string",  "category": "ai", "description": "LLM API基础URL"},
        {"config_key": "ai.model",      "config_value": "qwen2.5:latest",           "config_type": "string",  "category": "ai", "description": "LLM模型名称"},
        {"config_key": "ai.api_key",    "config_value": "",                          "config_type": "string",  "category": "ai", "description": "API密钥（如需要）"},
        {"config_key": "ai.enabled",    "config_value": "true",                      "config_type": "boolean", "category": "ai", "description": "是否启用AI分析"},
        {"config_key": "ai.temperature","config_value": "0.7",                       "config_type": "float",   "category": "ai", "description": "生成温度参数"},
        {"config_key": "ai.max_tokens", "config_value": "2048",                      "config_type": "integer", "category": "ai", "description": "最大生成token数"},
        {"config_key": "ai.timeout",    "config_value": "60",                        "config_type": "integer", "category": "ai", "description": "请求超时时间(秒)"},
        {"config_key": "ai.max_cases",  "config_value": "100",                       "config_type": "integer", "category": "ai", "description": "单次AI分析最大用例数"},
    ]

    # 默认配置查找表（用于 set_config 创建新文档时填充元信息）
    _DEFAULTS_MAP: dict[str, dict[str, str]] = {c["config_key"]: c for c in DEFAULT_CONFIGS}

    # 值类型解析器
    _PARSERS: dict[str, Any] = {
        "integer": int,
        "float": float,
        "boolean": lambda v: v.lower() in ("true", "1", "yes", "on"),
        "json": json.loads,
    }

    # AI 配置键 → AIConfig 字段映射
    _AI_CONFIG_MAPPING: dict[str, str] = {
        "ai.base_url": "base_url",
        "ai.model": "model",
        "ai.api_key": "api_key",
        "ai.enabled": "enabled",
        "ai.temperature": "temperature",
        "ai.max_tokens": "max_tokens",
        "ai.timeout": "timeout",
    }

    # ── 配置读取 ────────────────────────────────────────────

    @staticmethod
    async def get_config(key: str, default: Any = None) -> Any:
        """获取配置值（带缓存）"""
        cached = await ConfigCache.get(key)
        if cached is not None:
            return cached

        doc = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == key)
        if doc is None or not doc.is_active:
            return default

        value = ConfigService._parse_value(doc.config_value, doc.config_type)
        await ConfigCache.set(key, value)
        return value

    @staticmethod
    async def get_config_by_key(config_key: str) -> Optional[SystemConfigDoc]:
        """获取单个配置文档"""
        return await SystemConfigDoc.find_one(SystemConfigDoc.config_key == config_key)

    @staticmethod
    async def get_configs(
        category: Optional[str] = None,
        active_only: bool = True,
        search: Optional[str] = None,
    ) -> tuple[list[SystemConfigDoc], int]:
        """获取配置列表"""
        query: dict[str, Any] = {}
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
        """获取所有配置分类"""
        docs = await SystemConfigDoc.all().to_list()
        return sorted(set(doc.category for doc in docs)) or ["ai", "system", "general"]

    @staticmethod
    async def get_ai_config() -> dict[str, Any]:
        """获取AI相关配置（用于LLM调用）"""
        config = AIConfig()
        for key, field in ConfigService._AI_CONFIG_MAPPING.items():
            value = await ConfigService.get_config(key)
            if value is not None:
                setattr(config, field, value)
        return config.model_dump()

    # ── 配置写入 ────────────────────────────────────────────

    @staticmethod
    async def set_config(
        key: str, value: Any,
        changed_by: Optional[str] = None, remark: Optional[str] = None,
    ) -> SystemConfigDoc:
        """设置配置值（自动记录历史）"""
        doc = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == key)
        if doc:
            await ConfigService._save_history(key, doc.config_value, str(value), changed_by, remark)
            doc.config_value = str(value)
            doc.updated_at = datetime.utcnow()
            doc.updated_by = changed_by
        else:
            default = ConfigService._DEFAULTS_MAP.get(key, {})
            doc = SystemConfigDoc(
                config_key=key, config_value=str(value),
                config_type=default.get("config_type", "string"),
                category=default.get("category", "general"),
                description=default.get("description"),
                is_encrypted=default.get("is_encrypted", False),
                updated_by=changed_by,
            )

        await (doc.save() if doc.id else doc.insert())
        await ConfigCache.invalidate(key)
        return doc

    @staticmethod
    async def batch_update(
        items: list[dict[str, str]],
        changed_by: Optional[str] = None, remark: Optional[str] = None,
    ) -> int:
        """批量更新配置"""
        count = 0
        for item in items:
            key, value = item.get("config_key"), item.get("config_value")
            if key and value is not None:
                await ConfigService.set_config(key, value, changed_by, remark)
                count += 1
        return count

    # ── 缓存 & 初始化 ──────────────────────────────────────

    @staticmethod
    async def reload_config(key: Optional[str] = None) -> None:
        """热加载配置（清除缓存）"""
        await ConfigCache.invalidate(key)

    @staticmethod
    async def init_default_configs() -> None:
        """初始化默认配置（仅创建缺失的）"""
        for cfg in ConfigService.DEFAULT_CONFIGS:
            existing = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == cfg["config_key"])
            if not existing:
                await SystemConfigDoc(**cfg).insert()
                log.info(f"Initialized config: {cfg['config_key']} = {cfg['config_value']}")

    # ── AI 连接测试 ─────────────────────────────────────────

    @staticmethod
    async def test_ai_connection(
        base_url: str, model: str,
        api_key: Optional[str] = None, timeout: int = 60,
    ) -> dict[str, Any]:
        """测试AI服务连接"""
        start = time.time()
        try:
            import openai
            client = openai.OpenAI(base_url=base_url, api_key=api_key or "ollama", timeout=timeout)
            response = client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": "Hi"}], max_tokens=10,
            )
            return {"success": True, "model": response.model,
                    "response_time_ms": int((time.time() - start) * 1000)}
        except Exception as e:
            log.error(f"AI connection test failed: {e}")
            return {"success": False, "error": str(e),
                    "response_time_ms": int((time.time() - start) * 1000)}

    # ── 历史记录 ────────────────────────────────────────────

    @staticmethod
    async def get_history(config_key: Optional[str] = None, limit: int = 50) -> list[SystemConfigHistoryDoc]:
        """获取配置历史"""
        query: dict[str, Any] = {}
        if config_key:
            query["config_key"] = config_key
        return await SystemConfigHistoryDoc.find(query).sort("-changed_at").limit(limit).to_list()

    @staticmethod
    async def _save_history(
        config_key: str, old_value: Optional[str], new_value: Optional[str],
        changed_by: Optional[str], remark: Optional[str],
    ) -> None:
        await SystemConfigHistoryDoc(
            config_key=config_key, old_value=old_value, new_value=new_value,
            changed_by=changed_by, remark=remark,
        ).insert()

    # ── 工具方法 ────────────────────────────────────────────

    @staticmethod
    def _parse_value(value: str, config_type: str) -> Any:
        """根据类型解析配置值"""
        parser = ConfigService._PARSERS.get(config_type)
        if not parser:
            return value
        try:
            return parser(value)
        except (ValueError, json.JSONDecodeError):
            return value


class ConfigValidator:
    """配置验证器"""

    # 验证规则：config_key → (解析函数, 约束描述)
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
        """验证配置值，返回 (是否有效, 错误信息)"""
        rule = ConfigValidator._RULES.get(config_key)
        if not rule:
            return True, ""

        checker, error_msg = rule
        try:
            if not checker(config_value):
                return False, error_msg
        except (ValueError, TypeError):
            return False, error_msg

        # base_url 额外校验 URL 格式
        if config_key == "ai.base_url":
            from urllib.parse import urlparse
            try:
                urlparse(config_value)
            except Exception:
                return False, "无效的URL格式"

        return True, ""
