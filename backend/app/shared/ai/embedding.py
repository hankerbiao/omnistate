"""Embedding 服务 — 调用本地 embedding API 生成文本向量。

API 地址和模型名从系统配置热加载（ai.embedding_base_url / ai.embedding_model），
支持运行时修改，无需重启。
"""
from __future__ import annotations

from typing import Any

import httpx

from app.shared.core.logger import log


class EmbeddingService:
    """Embedding 向量生成服务。"""

    @staticmethod
    async def embed_text(text: str) -> list[float] | None:
        """将单段文本转成 embedding 向量。

        Args:
            text: 要向量化的文本

        Returns:
            384/768/1024 维向量（取决于模型），出错时返回 None
        """
        from app.modules.system_config.service.config_service import ConfigService

        config = await ConfigService.get_ai_config()
        base_url = config.get("embedding_base_url", "") or "http://10.8.136.35:8002/v1"
        model = config.get("embedding_model", "") or "qwen3-vl-embedding"

        if not base_url:
            log.warning("embedding: base_url 未配置，跳过")
            return None

        url = f"{base_url.rstrip('/')}/embeddings"
        payload = {"input": text, "model": model}
        timeout = int(config.get("timeout", 60))

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            log.error("embedding: API 调用失败: {}", e)
            return None

        try:
            vector = data["data"][0]["embedding"]
            log.info("embedding: 生成成功 dim={} len={}chars", len(vector), len(text))
            return vector
        except (KeyError, IndexError, TypeError) as e:
            log.error("embedding: 解析响应失败: {} — {}", e, data)
            return None

    @staticmethod
    def build_case_text(
        title: str,
        *,
        test_category: str = "",
        tags: list[str] | None = None,
        pre_condition: str = "",
        post_condition: str = "",
        steps: list[dict[str, str]] | None = None,
    ) -> str:
        """拼接测试用例文本，供 embedding API 使用。"""
        parts = [f"用例: {title}"]
        if test_category:
            parts.append(f"分类: {test_category}")
        if tags:
            parts.append(f"标签: {', '.join(tags)}")
        if pre_condition:
            parts.append(f"前置: {pre_condition}")
        if post_condition:
            parts.append(f"后置: {post_condition}")
        if steps:
            step_texts = []
            for i, s in enumerate(steps, 1):
                name = s.get("name", "")
                action = s.get("action", "")
                expected = s.get("expected", "")
                step_texts.append(f"步骤{i}: {name} — {action} → {expected}")
            parts.append("; ".join(step_texts))
        return " | ".join(parts)

    @staticmethod
    def build_requirement_text(
        title: str,
        *,
        description: str = "",
        acceptance_criteria: str = "",
        category: str = "",
        tags: list[str] | None = None,
        risk_points: str = "",
    ) -> str:
        """拼接需求文本，供 embedding API 使用。"""
        parts = [f"需求: {title}"]
        if category:
            parts.append(f"分类: {category}")
        if tags:
            parts.append(f"标签: {', '.join(tags)}")
        if description:
            parts.append(f"描述: {description}")
        if acceptance_criteria:
            parts.append(f"验收标准: {acceptance_criteria}")
        if risk_points:
            parts.append(f"风险: {risk_points}")
        return " | ".join(parts)
