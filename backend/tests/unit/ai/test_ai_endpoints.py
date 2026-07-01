"""AI 端点单元测试：generate-cases + failure-analysis/analyze。"""
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


# ═══════════════════════════════════════════════════════════════════════
#  failure-analysis/analyze
# ═══════════════════════════════════════════════════════════════════════

async def test_analyze_failure_success():
    """AI 失败根因分析正常调用。"""
    from app.modules.failure_analysis.api.routes import AnalyzeFailureRequest
    from app.modules.failure_analysis.service import FailureAnalysisService

    mock_raw = {
        "root_cause_category": "code_defect",
        "confidence": 0.85,
        "analysis": "登录接口在并发场景下产生竞态条件，导致 session 写入冲突。",
        "probable_cause": "Redis session 写入缺少分布式锁",
        "fix_suggestions": [
            "在 session 写入逻辑中增加分布式锁",
            "增加 session 写入重试机制",
        ],
        "related_patterns": ["并发场景下的资源竞争"],
        "severity": "high",
    }

    # 用例不存在时，service 返回 None，路由 fallback 到空步骤
    mock_service = MagicMock(spec=FailureAnalysisService)
    mock_service.fetch_case_for_ai_analysis = AsyncMock(return_value=None)

    with patch("app.shared.ai.client.AIClient.get_instance") as get_instance:
        client = MagicMock()
        client.chat_completion_json = AsyncMock(return_value=mock_raw)
        get_instance.return_value = client

        from app.modules.failure_analysis.api.routes import analyze_failure
        req = AnalyzeFailureRequest(
            task_id="TASK-001",
            case_id="TC-001",
            execution_log="AssertionError: expected 200 got 500",
            failure_info="HTTP 500 Internal Server Error",
            env_info="Python 3.12, Redis 7.0",
        )
        response = await analyze_failure(req, mock_service)

    data = response.data
    assert data.root_cause_category == "code_defect"
    assert data.confidence == 0.85
    assert "分布式锁" in data.probable_cause
    assert len(data.fix_suggestions) == 2
    assert data.severity == "high"


async def test_analyze_failure_requires_input():
    """不提供 execution_log 或 failure_info 应报 400。"""
    from fastapi import HTTPException
    from app.modules.failure_analysis.api.routes import AnalyzeFailureRequest, analyze_failure

    req = AnalyzeFailureRequest(task_id="T1", case_id="C1")
    with pytest.raises(HTTPException) as exc_info:
        await analyze_failure(req)
    assert exc_info.value.status_code == 400


async def test_analyze_failure_with_test_case_steps():
    """用例存在时，步骤信息应被包含在 prompt 中。"""
    from app.modules.failure_analysis.api.routes import AnalyzeFailureRequest
    from app.modules.failure_analysis.service import FailureAnalysisService

    mock_raw = {
        "root_cause_category": "test_case",
        "confidence": 0.7,
        "analysis": "用例步骤的预期结果不可验证。",
        "probable_cause": "预期结果描述过于模糊",
        "fix_suggestions": ["明确预期结果为具体的 HTTP 状态码"],
        "related_patterns": [],
        "severity": "medium",
    }

    steps = [
        {
            "step_id": "step-1",
            "name": "登录",
            "action": "POST /api/login",
            "expected": "成功",
        }
    ]
    mock_service = MagicMock(spec=FailureAnalysisService)
    mock_service.fetch_case_for_ai_analysis = AsyncMock(
        return_value={
            "case_title": "登录测试",
            "steps_json": json.dumps(steps, ensure_ascii=False, indent=2),
        }
    )

    captured_user_content: list[str] = []

    async def _capture_chat(system_prompt, user_content, **kwargs):
        captured_user_content.append(user_content)
        return mock_raw

    with patch("app.shared.ai.client.AIClient.get_instance") as get_instance:
        client = MagicMock()
        client.chat_completion_json = _capture_chat
        get_instance.return_value = client

        from app.modules.failure_analysis.api.routes import analyze_failure
        req = AnalyzeFailureRequest(
            task_id="TASK-002",
            case_id="TC-002",
            execution_log="some log",
            failure_info="test failed",
        )
        response = await analyze_failure(req, mock_service)

    assert "登录测试" in captured_user_content[0]
    assert "POST /api/login" in captured_user_content[0]
    assert response.data.root_cause_category == "test_case"
