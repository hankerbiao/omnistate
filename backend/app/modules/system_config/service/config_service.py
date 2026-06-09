"""
系统配置服务层

提供配置的 CRUD、热加载、缓存和 AI 连接测试功能
"""
import asyncio
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
    DEFAULT_CONFIGS = [
        # AI 配置
        {"config_key": "ai.base_url", "config_value": "http://localhost:11434/v1", "config_type": "string", "category": "ai", "description": "LLM API基础URL"},
        {"config_key": "ai.model", "config_value": "qwen2.5:latest", "config_type": "string", "category": "ai", "description": "LLM模型名称"},
        {"config_key": "ai.api_key", "config_value": "", "config_type": "string", "category": "ai", "description": "API密钥（如需要）", "is_encrypted": True},
        {"config_key": "ai.enabled", "config_value": "true", "config_type": "boolean", "category": "ai", "description": "是否启用AI分析"},
        {"config_key": "ai.temperature", "config_value": "0.7", "config_type": "float", "category": "ai", "description": "生成温度参数"},
        {"config_key": "ai.max_tokens", "config_value": "4096", "config_type": "integer", "category": "ai", "description": "最大生成token数"},
        {"config_key": "ai.timeout", "config_value": "60", "config_type": "integer", "category": "ai", "description": "请求超时时间(秒)"},
        # 系统配置
        {"config_key": "system.site_name", "config_value": "DML测试平台", "config_type": "string", "category": "system", "description": "站点名称"},
        {"config_key": "system.max_upload_size", "config_value": "10485760", "config_type": "integer", "category": "system", "description": "最大上传文件大小(字节)"},
        {"config_key": "system.allowed_file_types", "config_value": ".pdf,.txt,.json", "config_type": "string", "category": "system", "description": "允许上传的文件类型"},
    ]

    @staticmethod
    async def get_config(key: str, default: Any = None) -> Any:
        """获取配置值（带缓存）"""
        # 先查缓存
        cached = await ConfigCache.get(key)
        if cached is not None:
            return cached

        # 查数据库
        doc = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == key, SystemConfigDoc.is_active is True)
        if doc is None:
            return default

        # 转换类型
        value = ConfigService._parse_value(doc.config_value, doc.config_type)
        await ConfigCache.set(key, value)
        return value

    @staticmethod
    async def set_config(key: str, value: Any, changed_by: Optional[str] = None, remark: Optional[str] = None) -> SystemConfigDoc:
        """设置配置值（自动记录历史）"""
        doc = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == key)

        # 记录历史
        if doc:
            await ConfigService._save_history(key, doc.config_value, str(value), changed_by, remark)

        # 更新或创建配置
        if doc:
            doc.config_value = str(value)
            doc.updated_at = datetime.utcnow()
            doc.updated_by = changed_by
            await doc.save()
        else:
            # 从默认配置中获取类型信息
            default_item = next((c for c in ConfigService.DEFAULT_CONFIGS if c["config_key"] == key), {})
            doc = SystemConfigDoc(
                config_key=key,
                config_value=str(value),
                config_type=default_item.get("config_type", "string"),
                category=default_item.get("category", "general"),
                description=default_item.get("description"),
                is_encrypted=default_item.get("is_encrypted", False),
                updated_by=changed_by,
            )
            await doc.insert()

        # 清除缓存
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
        start_time = time.time()

        try:
            import openai

            client = openai.OpenAI(
                base_url=base_url,
                api_key=api_key or "ollama",  # Ollama不需要真实key
                timeout=timeout,
            )

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10,
            )

            actual_model = response.model
            response_time_ms = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "model": actual_model,
                "response_time_ms": response_time_ms,
            }

        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            log.error(f"AI connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "response_time_ms": response_time_ms,
            }

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

    @staticmethod
    async def init_default_configs() -> None:
        """初始化默认配置（仅创建缺失的）"""
        for config in ConfigService.DEFAULT_CONFIGS:
            existing = await SystemConfigDoc.find_one(SystemConfigDoc.config_key == config["config_key"])
            if not existing:
                doc = SystemConfigDoc(**config)
                await doc.insert()
                log.info(f"Initialized config: {config['config_key']}")

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
            if config_type == "integer":
                return int(value)
            elif config_type == "float":
                return float(value)
            elif config_type == "boolean":
                return value.lower() in ("true", "1", "yes", "on")
            elif config_type == "json":
                import json
                return json.loads(value)
            else:
                return value
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
                if val < 1 or val > 100000:
                    return False, "Token数量必须在1-100000之间"
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
