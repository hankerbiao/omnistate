"""共享 AI 客户端封装。

统一管理 OpenAI 兼容客户端的创建、配置读取、重试和调用审计。
所有业务模块的 AI 功能必须通过 AIClient 调用，不允许直接创建 OpenAI 实例。
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from openai import AsyncOpenAI

from app.shared.core.logger import log


class AICallResult(dict):
    """AI 调用结果，兼容 dict 访问的同时提供属性方式。"""

    @property
    def content(self) -> str:
        return self.get("content", "")

    @property
    def model(self) -> str:
        return self.get("model", "")

    @property
    def elapsed_ms(self) -> int:
        return self.get("elapsed_ms", 0)

    @property
    def usage(self) -> dict[str, int] | None:
        return self.get("usage")


class AIClient:
    """共享 AI 客户端单例。

    使用方式::

        from app.shared.ai.client import AIClient

        client = AIClient.get_instance()
        result = await client.chat_completion(
            messages=[
                {"role": "system", "content": "你是测试专家"},
                {"role": "user", "content": "分析这个用例..."},
            ],
        )
        print(result.content)
    """

    _instance: AIClient | None = None
    _cached_client: AsyncOpenAI | None = None
    _cached_config_key: str | None = None

    def __init__(self) -> None:
        self._max_retries: int = 3
        self._retry_base_delay: float = 1.0

    @classmethod
    def get_instance(cls) -> AIClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例（测试用）。"""
        cls._instance = None
        cls._cached_client = None
        cls._cached_config_key = None

    async def get_config(self) -> dict[str, Any]:
        """获取当前 AI 配置。"""
        from app.modules.system_config.service.config_service import ConfigService
        return await ConfigService.get_ai_config()

    def _build_client(self, config: dict[str, Any]) -> AsyncOpenAI:
        base_url = config.get("base_url", "")
        api_key = config.get("api_key") or "ollama"
        timeout = int(config.get("timeout", 60))
        return AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout)

    async def get_client(self) -> AsyncOpenAI | None:
        """获取 OpenAI 客户端。

        配置变更时自动重建（通过 config key 比对）。
        ai.enabled=false 时返回 None。
        """
        config = await self.get_config()

        if not config.get("enabled", True):
            log.warning("AI 功能未启用（ai.enabled = false）")
            return None

        base_url = config.get("base_url", "")
        model = config.get("model", "")
        if not base_url or not model:
            log.warning("AI 配置不完整（base_url 或 model 为空）")
            return None

        config_key = f"{base_url}:{model}:{config.get('timeout', 60)}"
        if self._cached_client is not None and self._cached_config_key == config_key:
            return self._cached_client

        self._cached_client = self._build_client(config)
        self._cached_config_key = config_key
        return self._cached_client

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> AICallResult:
        """调用 LLM chat completion，带重试和审计。

        Returns:
            AICallResult 包含 content / model / elapsed_ms / usage

        Raises:
            RuntimeError: AI 未启用或配置不完整
            Exception: LLM 调用失败（重试后）
        """
        config = await self.get_config()
        if not config.get("enabled", True):
            raise RuntimeError("AI 功能未启用")

        base_url = config.get("base_url", "")
        model = config.get("model", "")
        if not base_url or not model:
            raise RuntimeError("AI 配置不完整（base_url 或 model 为空）")

        client = await self.get_client()
        if client is None:
            raise RuntimeError("无法创建 AI 客户端")

        temp = temperature if temperature is not None else float(config.get("temperature", 0.7))
        tokens = max_tokens if max_tokens is not None else int(config.get("max_tokens", 2048))

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                start = time.monotonic()
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                )
                elapsed_ms = int((time.monotonic() - start) * 1000)

                content = response.choices[0].message.content or ""
                usage = None
                if response.usage:
                    usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }

                log.info(
                    "AI call: model={} elapsed={}ms tokens={} attempt={}/{}",
                    model, elapsed_ms,
                    usage.get("total_tokens") if usage else "N/A",
                    attempt, self._max_retries,
                )

                return AICallResult(
                    content=content,
                    model=model,
                    elapsed_ms=elapsed_ms,
                    usage=usage,
                )

            except Exception as exc:
                last_error = exc
                if attempt < self._max_retries:
                    delay = self._retry_base_delay * (2 ** (attempt - 1))
                    log.warning(
                        "AI call attempt {}/{} failed: {} — retrying in {:.1f}s",
                        attempt, self._max_retries, exc, delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    log.error("AI call failed after {} attempts: {}", self._max_retries, exc)

        raise last_error  # type: ignore[misc]

    async def simple_chat(
        self,
        system_prompt: str,
        user_content: str,
        **kwargs: Any,
    ) -> str:
        """简化调用，直接返回 content 字符串。"""
        result = await self.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            **kwargs,
        )
        return result.content

    async def chat_completion_json(
        self,
        system_prompt: str,
        user_content: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """调用 LLM 并解析 JSON 响应。

        自动清理 markdown 代码块标记后 json.loads。
        """
        content = await self.simple_chat(system_prompt, user_content, **kwargs)
        return self._parse_json(content)

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        """清理 markdown 代码块并解析 JSON。"""
        content = content.strip()
        if content.startswith("```"):
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1:]
            if content.endswith("```"):
                content = content[:-3].strip()
            elif "```" in content:
                content = content[: content.rfind("```")].strip()
        return json.loads(content)
