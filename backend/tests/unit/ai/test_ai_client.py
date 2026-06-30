"""AIClient 共享客户端单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.ai.client import AIClient, AICallResult  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
#  AICallResult
# ═══════════════════════════════════════════════════════════════════════

def test_aicallresult_property_access():
    result = AICallResult(content="hello", model="qwen2.5", elapsed_ms=150, usage={"total_tokens": 42})
    assert result.content == "hello"
    assert result.model == "qwen2.5"
    assert result.elapsed_ms == 150
    assert result.usage["total_tokens"] == 42


def test_aicallresult_dict_access():
    result = AICallResult(content="hello", model="qwen2.5", elapsed_ms=150)
    assert result["content"] == "hello"
    assert result["model"] == "qwen2.5"


def test_aicallresult_defaults():
    result = AICallResult()
    assert result.content == ""
    assert result.model == ""
    assert result.elapsed_ms == 0
    assert result.usage is None


# ═══════════════════════════════════════════════════════════════════════
#  AIClient singleton
# ═══════════════════════════════════════════════════════════════════════

def test_singleton_returns_same_instance():
    AIClient.reset()
    a = AIClient.get_instance()
    b = AIClient.get_instance()
    assert a is b


def test_reset_creates_new_instance():
    AIClient.reset()
    a = AIClient.get_instance()
    AIClient.reset()
    b = AIClient.get_instance()
    assert a is not b


# ═══════════════════════════════════════════════════════════════════════
#  get_client
# ═══════════════════════════════════════════════════════════════════════

async def test_get_client_returns_none_when_disabled():
    AIClient.reset()
    client = AIClient.get_instance()
    with patch.object(client, "get_config", AsyncMock(return_value={"enabled": False})):
        result = await client.get_client()
        assert result is None


async def test_get_client_returns_none_when_base_url_missing():
    AIClient.reset()
    client = AIClient.get_instance()
    config = {"enabled": True, "base_url": "", "model": "qwen"}
    with patch.object(client, "get_config", AsyncMock(return_value=config)):
        result = await client.get_client()
        assert result is None


async def test_get_client_returns_none_when_model_missing():
    AIClient.reset()
    client = AIClient.get_instance()
    config = {"enabled": True, "base_url": "http://localhost:11434/v1", "model": ""}
    with patch.object(client, "get_config", AsyncMock(return_value=config)):
        result = await client.get_client()
        assert result is None


async def test_get_client_caches_client():
    AIClient.reset()
    client = AIClient.get_instance()
    config = {
        "enabled": True,
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5",
        "api_key": "ollama",
        "timeout": 60,
    }
    with patch.object(client, "get_config", AsyncMock(return_value=config)):
        c1 = await client.get_client()
        c2 = await client.get_client()
        assert c1 is c2


async def test_get_client_rebuilds_on_config_change():
    AIClient.reset()
    client = AIClient.get_instance()
    config1 = {"enabled": True, "base_url": "http://a/v1", "model": "m1", "api_key": "k", "timeout": 60}
    config2 = {"enabled": True, "base_url": "http://b/v1", "model": "m2", "api_key": "k", "timeout": 60}
    with patch.object(client, "get_config", AsyncMock(side_effect=[config1, config2])):
        c1 = await client.get_client()
        c2 = await client.get_client()
        assert c1 is not c2


# ═══════════════════════════════════════════════════════════════════════
#  chat_completion
# ═══════════════════════════════════════════════════════════════════════

async def test_chat_completion_raises_when_disabled():
    AIClient.reset()
    client = AIClient.get_instance()
    with patch.object(client, "get_config", AsyncMock(return_value={"enabled": False})):
        with pytest.raises(RuntimeError, match="未启用"):
            await client.chat_completion(messages=[])


async def test_chat_completion_raises_when_config_incomplete():
    AIClient.reset()
    client = AIClient.get_instance()
    config = {"enabled": True, "base_url": "", "model": ""}
    with patch.object(client, "get_config", AsyncMock(return_value=config)):
        with pytest.raises(RuntimeError, match="不完整"):
            await client.chat_completion(messages=[])


async def test_chat_completion_success():
    AIClient.reset()
    client = AIClient.get_instance()
    config = {
        "enabled": True,
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5",
        "api_key": "ollama",
        "timeout": 60,
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "AI response"
    mock_response.usage = MagicMock(
        prompt_tokens=10, completion_tokens=5, total_tokens=15,
    )
    mock_openai_client.chat.completions.create = MagicMock(return_value=mock_response)

    with patch.object(client, "get_config", AsyncMock(return_value=config)):
        with patch.object(client, "get_client", AsyncMock(return_value=mock_openai_client)):
            result = await client.chat_completion(
                messages=[{"role": "user", "content": "hi"}],
            )

    assert result.content == "AI response"
    assert result.model == "qwen2.5"
    assert result.usage["total_tokens"] == 15
    assert result.elapsed_ms >= 0


async def test_chat_completion_retries_on_failure():
    AIClient.reset()
    client = AIClient._instance = AIClient()
    client._max_retries = 2
    client._retry_base_delay = 0.01  # 加速测试

    config = {
        "enabled": True,
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5",
        "api_key": "ollama",
        "timeout": 60,
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    mock_openai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "success"
    mock_response.usage = None

    # 第一次抛异常，第二次成功
    mock_openai_client.chat.completions.create = MagicMock(
        side_effect=[Exception("network error"), mock_response]
    )

    with patch.object(client, "get_config", AsyncMock(return_value=config)):
        with patch.object(client, "get_client", AsyncMock(return_value=mock_openai_client)):
            result = await client.chat_completion(messages=[{"role": "user", "content": "hi"}])

    assert result.content == "success"
    assert mock_openai_client.chat.completions.create.call_count == 2


async def test_chat_completion_fails_after_max_retries():
    AIClient.reset()
    client = AIClient.get_instance()
    client._max_retries = 2
    client._retry_base_delay = 0.01

    config = {
        "enabled": True,
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5",
        "api_key": "ollama",
        "timeout": 60,
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create = MagicMock(
        side_effect=Exception("persistent error")
    )

    with patch.object(client, "get_config", AsyncMock(return_value=config)):
        with patch.object(client, "get_client", AsyncMock(return_value=mock_openai_client)):
            with pytest.raises(Exception, match="persistent error"):
                await client.chat_completion(messages=[])

    assert mock_openai_client.chat.completions.create.call_count == 2


# ═══════════════════════════════════════════════════════════════════════
#  simple_chat / chat_completion_json
# ═══════════════════════════════════════════════════════════════════════

async def test_simple_chat_returns_content_string():
    AIClient.reset()
    client = AIClient.get_instance()

    mock_result = AICallResult(content="hello world", model="qwen", elapsed_ms=100, usage=None)
    with patch.object(client, "chat_completion", AsyncMock(return_value=mock_result)):
        result = await client.simple_chat("system prompt", "user content")

    assert result == "hello world"


async def test_chat_completion_json_parses_json():
    AIClient.reset()
    client = AIClient.get_instance()

    mock_result = AICallResult(content='{"score": 85, "issues": []}', model="qwen", elapsed_ms=100)
    with patch.object(client, "chat_completion", AsyncMock(return_value=mock_result)):
        result = await client.chat_completion_json("system", "user")

    assert result["score"] == 85
    assert result["issues"] == []


async def test_chat_completion_json_strips_markdown():
    AIClient.reset()
    client = AIClient.get_instance()

    mock_result = AICallResult(
        content='```json\n{"score": 90, "summary": "good"}\n```',
        model="qwen", elapsed_ms=100,
    )
    with patch.object(client, "chat_completion", AsyncMock(return_value=mock_result)):
        result = await client.chat_completion_json("system", "user")

    assert result["score"] == 90
    assert result["summary"] == "good"


# ═══════════════════════════════════════════════════════════════════════
#  _parse_json static method
# ═══════════════════════════════════════════════════════════════════════

def test_parse_json_plain():
    result = AIClient._parse_json('{"a": 1}')
    assert result == {"a": 1}


def test_parse_json_with_markdown_block():
    result = AIClient._parse_json('```json\n{"a": 1}\n```')
    assert result == {"a": 1}


def test_parse_json_with_bare_markdown():
    result = AIClient._parse_json('```\n{"a": 1}\n```')
    assert result == {"a": 1}


def test_parse_json_with_trailing_whitespace():
    result = AIClient._parse_json('  {"a": 1}  ')
    assert result == {"a": 1}
