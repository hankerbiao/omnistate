"""AI 端点单元测试：generate-cases。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.ai.client import AICallResult  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
#  generate-cases
# ═══════════════════════════════════════════════════════════════════════

async def test_generate_cases_with_text_requirement():
    """传 requirement_text 生成用例。"""
    from app.modules.system_config.api.ai_routes import GenerateCasesRequest

    mock_raw = {
        "cases": [
            {
                "title": "正常登录测试",
                "priority": "P1",
                "test_category": "functional",
                "pre_condition": "用户已注册",
                "post_condition": "退出登录",
                "steps": [
                    {"step_id": "step-1", "name": "打开登录页", "action": "访问 /login", "expected": "页面加载完成"},
                    {"step_id": "step-2", "name": "输入凭证", "action": "输入用户名和密码", "expected": "输入框显示正确"},
                ],
                "tags": ["登录", "认证"],
                "rationale": "验证正常登录流程",
            }
        ]
    }

    mock_result = AICallResult(
        content=json.dumps(mock_raw),
        model="qwen2.5",
        elapsed_ms=100,
    )

    with patch("app.shared.ai.client.AIClient.get_instance") as get_instance:
        client = MagicMock()
        client.chat_completion_json = AsyncMock(return_value=mock_raw)
        get_instance.return_value = client

        from app.modules.system_config.api.ai_routes import generate_cases
        req = GenerateCasesRequest(requirement_text="测试用户登录功能", max_cases=3)
        response = await generate_cases(req)

    data = response.data
    assert len(data.cases) == 1
    assert data.cases[0].title == "正常登录测试"
    assert data.cases[0].priority == "P1"
    assert len(data.cases[0].steps) == 2
    assert data.cases[0].steps[0].step_id == "step-1"
    assert "登录" in data.cases[0].tags


async def test_generate_cases_requires_input():
    """不提供 requirement_id 或 requirement_text 应报 400。"""
    from fastapi import HTTPException
    from app.modules.system_config.api.ai_routes import GenerateCasesRequest, generate_cases

    req = GenerateCasesRequest()
    with pytest.raises(HTTPException) as exc_info:
        await generate_cases(req)
    assert exc_info.value.status_code == 400


async def test_generate_cases_empty_result():
    """AI 返回空用例列表时正常响应。"""
    from app.modules.system_config.api.ai_routes import GenerateCasesRequest, generate_cases

    mock_raw = {"cases": [], "reason": "需求信息不足"}

    with patch("app.shared.ai.client.AIClient.get_instance") as get_instance:
        client = MagicMock()
        client.chat_completion_json = AsyncMock(return_value=mock_raw)
        get_instance.return_value = client

        req = GenerateCasesRequest(requirement_text="测试", max_cases=1)
        response = await generate_cases(req)

    assert len(response.data.cases) == 0
    assert response.data.reason == "需求信息不足"


async def test_generate_cases_with_requirement_id_not_found():
    """需求 ID 不存在时报 404。"""
    from fastapi import HTTPException
    from app.modules.system_config.api.ai_routes import GenerateCasesRequest

    with patch(
        "app.modules.test_specs.repository.models.requirement.TestRequirementDoc",
    ) as MockReqDoc:
        MockReqDoc.find_one = AsyncMock(return_value=None)
        MockReqDoc.req_id = MagicMock()
        MockReqDoc.is_deleted = MagicMock()

        from app.modules.system_config.api.ai_routes import generate_cases
        req = GenerateCasesRequest(requirement_id="TR-NOT-EXIST")
        with pytest.raises(HTTPException) as exc_info:
            await generate_cases(req)
        assert exc_info.value.status_code == 404
