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


# ── 辅助函数 ─────────────────────────────────────────────

def _cfg(key: str, value: str, type: str, cat: str, desc: str) -> dict:
    """构建配置项字典，减少 DEFAULT_CONFIGS 的重复代码

    注意：所有配置项均存储在 MongoDB 中。
    需要重启生效的基础设施配置（execution.*, jwt.*, logging.*, app.*）
    定义在 config.yaml 中，不在此处重复定义。
    """
    return {"config_key": key, "config_value": value, "config_type": type,
            "category": cat, "description": desc}


class ConfigCache:
    """配置缓存管理器"""

    _cache: dict[str, tuple[Any, float]] = {}
    _lock = asyncio.Lock()
    _cache_ttl: float = 300  # 5分钟缓存

    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        """从缓存获取配置值"""
        async with cls._lock:
            if key in cls._cache:
                value, timestamp = cls._cache[key]
                if time.time() - timestamp < cls._cache_ttl:
                    return value
                else:
                    del cls._cache[key]
            return None

    @classmethod
    async def set(cls, key: str, value: Any) -> None:
        """设置缓存"""
        async with cls._lock:
            cls._cache[key] = (value, time.time())

    @classmethod
    async def invalidate(cls, key: Optional[str] = None) -> None:
        """清除缓存"""
        async with cls._lock:
            if key is None:
                cls._cache.clear()
                log.info("ConfigCache: all entries cleared")
            elif key in cls._cache:
                del cls._cache[key]
                log.debug(f"ConfigCache: key={key} invalidated")


class ConfigService:
    """系统配置服务"""

    # 预置配置项
    # 仅包含运行时可热修改的配置（AI 配置 + 系统展示配置）。
    # 需要重启的基础设施配置（execution.*, jwt.*, logging.*, app.*）统一在 config.yaml 中管理。
    DEFAULT_CONFIGS = [
        # AI 配置
        _cfg("ai.base_url", "http://localhost:11434/v1", "string", "ai", "LLM API基础URL"),
        _cfg("ai.model", "qwen2.5:latest", "string", "ai", "LLM模型名称"),
        _cfg("ai.api_key", "", "string", "ai", "API密钥（如需要）"),
        _cfg("ai.enabled", "true", "boolean", "ai", "是否启用AI分析"),
        _cfg("ai.temperature", "0.7", "float", "ai", "生成温度参数"),
        _cfg("ai.max_tokens", "2048", "integer", "ai", "最大生成token数"),
        _cfg("ai.timeout", "60", "integer", "ai", "请求超时时间(秒)"),
        _cfg("ai.max_cases", "100", "integer", "ai", "单次AI分析最大用例数"),
    ]

    @staticmethod
    async def get_config(key: str, default: Any = None) -> Any:
        """获取配置值（带缓存）"""
        # 先查缓存
        cached = await ConfigCache.get(key)
        if cached is not None:
            return cached

        # 查数据库
        doc = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == key)
        if doc is None or not doc.is_active:
            return default

        # 转换类型
        value = ConfigService._parse_value(doc.config_value, doc.config_type)
        await ConfigCache.set(key, value)
        return value

    @staticmethod
    async def set_config(key: str, value: Any, changed_by: Optional[str] = None, remark: Optional[str] = None) -> SystemConfigDoc:
        """设置配置值（自动记录历史）"""
        doc = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == key)
        if doc:
            await ConfigService._save_history(key, doc.config_value, str(value), changed_by, remark)
            doc.config_value = str(value)
            doc.updated_at = datetime.utcnow()
            doc.updated_by = changed_by
        else:
            default = next((c for c in ConfigService.DEFAULT_CONFIGS if c["config_key"] == key), {})
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
    async def get_ai_config() -> dict[str, Any]:
        """获取AI相关配置（用于LLM调用）"""
        config = AIConfig()
        for key, field in [
            ("ai.base_url", "base_url"),
            ("ai.model", "model"),
            ("ai.api_key", "api_key"),
            ("ai.enabled", "enabled"),
            ("ai.temperature", "temperature"),
            ("ai.max_tokens", "max_tokens"),
            ("ai.timeout", "timeout"),
        ]:
            value = await ConfigService.get_config(key)
            if value is not None:
                setattr(config, field, value)
        return config.model_dump()

    @staticmethod
    async def test_ai_connection(base_url: str, model: str, api_key: Optional[str] = None, timeout: int = 60) -> dict[str, Any]:
        """测试AI服务连接"""
        start = time.time()
        try:
            import openai
            client = openai.OpenAI(base_url=base_url, api_key=api_key or "ollama", timeout=timeout)
            response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": "Hi"}], max_tokens=10)
            return {"success": True, "model": response.model, "response_time_ms": int((time.time() - start) * 1000)}
        except Exception as e:
            log.error(f"AI connection test failed: {e}")
            return {"success": False, "error": str(e), "response_time_ms": int((time.time() - start) * 1000)}

    @staticmethod
    async def reload_config(key: Optional[str] = None) -> None:
        """热加载配置（清除缓存）"""
        await ConfigCache.invalidate(key)

    @staticmethod
    async def get_configs(
        category: Optional[str] = None,
        active_only: bool = True,
        search: Optional[str] = None,
    ) -> tuple[list[SystemConfigDoc], int]:
        """获取配置列表"""
        query = {}

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
    async def get_config_by_key(config_key: str) -> Optional[SystemConfigDoc]:
        """获取单个配置"""
        return await SystemConfigDoc.find_one(SystemConfigDoc.config_key == config_key)

    @staticmethod
    async def get_categories() -> list[str]:
        """获取所有配置分类"""
        docs = await SystemConfigDoc.all().to_list()
        categories = sorted(set(doc.category for doc in docs))
        if not categories:
            categories = ["ai", "system", "general"]
        return categories

    @staticmethod
    async def batch_update(items: list[dict[str, str]], changed_by: Optional[str] = None, remark: Optional[str] = None) -> int:
        """批量更新配置"""
        count = 0
        for item in items:
            key = item.get("config_key")
            value = item.get("config_value")
            if key and value is not None:
                await ConfigService.set_config(key, value, changed_by, remark)
                count += 1
        return count

    @staticmethod
    async def get_history(config_key: Optional[str] = None, limit: int = 50) -> list[SystemConfigHistoryDoc]:
        """获取配置历史"""
        query = {}
        if config_key:
            query["config_key"] = config_key

        docs = (
            await SystemConfigHistoryDoc.find(query)
            .sort("-changed_at")
            .limit(limit)
            .to_list()
        )
        return docs

    # 需要重启生效的配置前缀
    RESTART_REQUIRED_PREFIXES = ("execution.", "jwt.", "logging.", "app.")

    @staticmethod
    def get_needs_restart(config_key: str) -> bool:
        """判断配置修改后是否需要重启生效"""
        return config_key.startswith(ConfigService.RESTART_REQUIRED_PREFIXES)

    @staticmethod
    async def init_default_configs() -> None:
        """初始化默认配置（仅创建缺失的）。

        所有配置项使用硬编码默认值。
        需要重启的基础设施配置由 config.yaml 管理，不在此处初始化。
        """
        for config in ConfigService.DEFAULT_CONFIGS:
            existing = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == config["config_key"])
            if not existing:
                doc = SystemConfigDoc(**config)
                await doc.insert()
                log.info(f"Initialized config: {config['config_key']} = {config['config_value']}")

    @staticmethod
    async def _save_history(
        config_key: str,
        old_value: Optional[str],
        new_value: Optional[str],
        changed_by: Optional[str],
        remark: Optional[str],
    ) -> None:
        """保存配置历史"""
        history = SystemConfigHistoryDoc(
            config_key=config_key,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            remark=remark,
        )
        await history.insert()

    @staticmethod
    def _parse_value(value: str, config_type: str) -> Any:
        """根据类型解析配置值"""
        try:
            parsers = {
                "integer": int,
                "float": float,
                "boolean": lambda v: v.lower() in ("true", "1", "yes", "on"),
                "json": json.loads,
            }
            parser = parsers.get(config_type)
            return parser(value) if parser else value
        except (ValueError, json.JSONDecodeError):
            return value


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate(config_key: str, config_value: str) -> tuple[bool, str]:
        """验证配置值，返回 (是否有效, 错误信息)"""
        from urllib.parse import urlparse

        if config_key == "ai.base_url":
            if config_value and not config_value.startswith(("http://", "https://")):
                return False, "URL必须以http://或https://开头"
            try:
                urlparse(config_value)
            except Exception:
                return False, "无效的URL格式"

        elif config_key == "ai.temperature":
            try:
                val = float(config_value)
                if not 0 <= val <= 2:
                    return False, "温度参数必须在0-2之间"
            except ValueError:
                return False, "必须是有效的数字"

        elif config_key == "ai.max_tokens":
            try:
                val = int(config_value)
                if val < 1:
                    return False, "Token数量不能小于1"
            except ValueError:
                return False, "必须是有效的整数"

        elif config_key == "ai.timeout":
            try:
                val = int(config_value)
                if val < 5 or val > 300:
                    return False, "超时时间必须在5-300秒之间"
            except ValueError:
                return False, "必须是有效的整数"

        return True, ""
