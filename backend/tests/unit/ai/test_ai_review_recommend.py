"""AI 端点单元测试：review-case + recommend-cases。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ═══════════════════════════════════════════════════════════════════════
#  review-case
# ═══════════════════════════════════════════════════════════════════════

async def test_review_case_success():
    """AI 用例评审正常调用。"""
    mock_raw = {
        "score": 78,
        "verdict": "needs_revision",
        "dimensions": {
            "completeness": {"score": 80, "issues": ["缺少边界条件测试"]},
            "clarity": {"score": 90, "issues": []},
            "traceability": {"score": 60, "issues": ["未关联需求"]},
            "executability": {"score": 82, "issues": ["前置条件不够具体"]},
        },
        "missing_scenarios": ["异常输入测试", "边界值测试"],
        "priority_suggestion": "P1",
        "summary": "用例基本可用，但需补充边界条件和异常路径。",
    }

    mock_step = MagicMock()
    mock_step.step_id = "s1"
    mock_step.name = "登录"
    mock_step.action = "输入账号密码"
    mock_step.expected = "登录成功"

    mock_doc = MagicMock()
    mock_doc.title = "登录测试"
    mock_doc.priority = "P1"
    mock_doc.test_category = "functional"
    mock_doc.tags = ["登录", "认证"]
    mock_doc.pre_condition = "用户已注册"
    mock_doc.post_condition = "退出登录"
    mock_doc.ref_req_id = "TR-001"
    mock_doc.steps = [mock_step]

    captured: list[str] = []

    async def _capture(system_prompt, user_content, **kwargs):
        captured.append(user_content)
        return mock_raw

    with patch("app.shared.ai.client.AIClient.get_instance") as get_instance:
        client = MagicMock()
        client.chat_completion_json = _capture
        get_instance.return_value = client

        with patch("app.modules.test_specs.repository.models.test_case.TestCaseDoc") as MockTC:
            MockTC.find_one = AsyncMock(return_value=mock_doc)
            MockTC.case_id = MagicMock()
            MockTC.is_deleted = MagicMock()

            from app.modules.system_config.api.ai_routes import ReviewCaseRequest, review_case
            req = ReviewCaseRequest(case_id="TC-001")
            response = await review_case(req)

    data = response.data
    assert data.score == 78
    assert data.verdict == "needs_revision"
    assert "completeness" in data.dimensions
    assert data.dimensions["completeness"].score == 80
    assert len(data.dimensions["completeness"].issues) == 1
    assert "异常输入测试" in data.missing_scenarios
    assert data.priority_suggestion == "P1"
    assert "登录测试" in captured[0]
    assert "TR-001" in captured[0]


async def test_review_case_not_found():
    """用例不存在时报 404。"""
    from fastapi import HTTPException

    with patch("app.modules.test_specs.repository.models.test_case.TestCaseDoc") as MockTC:
        MockTC.find_one = AsyncMock(return_value=None)
        MockTC.case_id = MagicMock()
        MockTC.is_deleted = MagicMock()

        from app.modules.system_config.api.ai_routes import ReviewCaseRequest, review_case
        req = ReviewCaseRequest(case_id="TC-NOT-EXIST")
        with pytest.raises(HTTPException) as exc_info:
            await review_case(req)
        assert exc_info.value.status_code == 404


async def test_review_case_no_steps():
    """用例没有步骤时仍能正常评审。"""
    mock_raw = {
        "score": 30,
        "verdict": "reject",
        "dimensions": {
            "completeness": {"score": 0, "issues": ["没有任何步骤"]},
        },
        "missing_scenarios": ["需要完整设计用例步骤"],
        "priority_suggestion": "保持不变",
        "summary": "用例为空，需重新设计。",
    }

    mock_doc = MagicMock()
    mock_doc.title = "空用例"
    mock_doc.priority = "P2"
    mock_doc.test_category = ""
    mock_doc.tags = []
    mock_doc.pre_condition = None
    mock_doc.post_condition = None
    mock_doc.ref_req_id = None
    mock_doc.steps = []

    with patch("app.shared.ai.client.AIClient.get_instance") as get_instance:
        client = MagicMock()
        client.chat_completion_json = AsyncMock(return_value=mock_raw)
        get_instance.return_value = client

        with patch("app.modules.test_specs.repository.models.test_case.TestCaseDoc") as MockTC:
            MockTC.find_one = AsyncMock(return_value=mock_doc)
            MockTC.case_id = MagicMock()
            MockTC.is_deleted = MagicMock()

            from app.modules.system_config.api.ai_routes import ReviewCaseRequest, review_case
            req = ReviewCaseRequest(case_id="TC-EMPTY")
            response = await review_case(req)

    assert response.data.verdict == "reject"
    assert response.data.score == 30


# ═══════════════════════════════════════════════════════════════════════
#  recommend-cases
# ═══════════════════════════════════════════════════════════════════════

async def test_recommend_cases_success():
    """AI 智能用例选择正常调用。"""
    mock_raw = {
        "recommended": [
            {"case_id": "TC-001", "reason": "直接覆盖变更模块", "priority_order": 1},
            {"case_id": "TC-003", "reason": "P0 回归用例", "priority_order": 2},
            {"case_id": "TC-005", "reason": "历史高频失败", "priority_order": 3},
        ],
        "excluded": [
            {"case_id": "TC-002", "reason": "与变更无关"},
        ],
        "coverage_note": "覆盖了变更模块的核心功能和回归场景，可能遗漏了兼容性测试。",
        "estimated_runtime_min": 45,
    }

    mock_docs = []
    for i in range(5):
        d = MagicMock()
        d.case_id = f"TC-00{i+1}"
        d.title = f"用例 {i+1}"
        d.priority = "P1" if i < 3 else "P2"
        d.test_category = "functional"
        d.tags = []
        mock_docs.append(d)

    mock_query = MagicMock()
    mock_query.to_list = AsyncMock(return_value=mock_docs)

    mock_tc_cls = MagicMock()
    mock_tc_cls.find = MagicMock(return_value=mock_query)
    mock_tc_cls.is_deleted = MagicMock()

    with patch("app.shared.ai.client.AIClient.get_instance") as get_instance:
        client = MagicMock()
        client.chat_completion_json = AsyncMock(return_value=mock_raw)
        get_instance.return_value = client

        with patch("app.modules.test_specs.repository.models.test_case.TestCaseDoc", mock_tc_cls):
            from app.modules.system_config.api.ai_routes import RecommendCasesRequest, recommend_cases
            req = RecommendCasesRequest(
                project_id="PROJ-1",
                change_description="修改了登录接口的 session 处理逻辑",
            )
            response = await recommend_cases(req)

    data = response.data
    assert len(data.recommended) == 3
    assert data.recommended[0].case_id == "TC-001"
    assert data.recommended[0].priority_order == 1
    assert len(data.excluded) == 1
    assert data.excluded[0].case_id == "TC-002"
    assert data.estimated_runtime_min == 45
    assert "核心功能" in data.coverage_note


async def test_recommend_cases_no_candidates():
    """没有候选用例时报 404。"""
    from fastapi import HTTPException

    mock_query = MagicMock()
    mock_query.to_list = AsyncMock(return_value=[])

    mock_tc_cls = MagicMock()
    mock_tc_cls.find = MagicMock(return_value=mock_query)
    mock_tc_cls.is_deleted = MagicMock()

    with patch("app.modules.test_specs.repository.models.test_case.TestCaseDoc", mock_tc_cls):
        from app.modules.system_config.api.ai_routes import RecommendCasesRequest, recommend_cases
        req = RecommendCasesRequest(change_description="some change")
        with pytest.raises(HTTPException) as exc_info:
            await recommend_cases(req)
        assert exc_info.value.status_code == 404


async def test_recommend_cases_respects_max_recommend():
    """推荐数受 max_recommend 限制。"""
    recs = []
    for i in range(10):
        recs.append({"case_id": f"TC-{i:03d}", "reason": f"理由{i}", "priority_order": i + 1})

    mock_raw = {"recommended": recs, "excluded": [], "coverage_note": "", "estimated_runtime_min": 30}

    mock_docs = [MagicMock(case_id=f"TC-{i:03d}", title=f"U{i}", priority="P1", test_category="", tags=[]) for i in range(10)]

    mock_query = MagicMock()
    mock_query.to_list = AsyncMock(return_value=mock_docs)

    mock_tc_cls = MagicMock()
    mock_tc_cls.find = MagicMock(return_value=mock_query)
    mock_tc_cls.is_deleted = MagicMock()

    with patch("app.shared.ai.client.AIClient.get_instance") as get_instance:
        client = MagicMock()
        client.chat_completion_json = AsyncMock(return_value=mock_raw)
        get_instance.return_value = client

        with patch("app.modules.test_specs.repository.models.test_case.TestCaseDoc", mock_tc_cls):
            from app.modules.system_config.api.ai_routes import RecommendCasesRequest, recommend_cases
            req = RecommendCasesRequest(
                change_description="test",
                max_recommend=3,
            )
            response = await recommend_cases(req)

    assert len(response.data.recommended) == 3
    assert response.data.recommended[0].priority_order == 1


async def test_recommend_cases_sorted_by_priority_order():
    """推荐结果按 priority_order 排序。"""
    mock_raw = {
        "recommended": [
            {"case_id": "TC-C", "reason": "third", "priority_order": 3},
            {"case_id": "TC-A", "reason": "first", "priority_order": 1},
            {"case_id": "TC-B", "reason": "second", "priority_order": 2},
        ],
        "excluded": [],
        "coverage_note": "",
        "estimated_runtime_min": 0,
    }

    mock_docs = [MagicMock(case_id="TC-X", title="U", priority="P1", test_category="", tags=[])]
    mock_query = MagicMock()
    mock_query.to_list = AsyncMock(return_value=mock_docs)

    mock_tc_cls = MagicMock()
    mock_tc_cls.find = MagicMock(return_value=mock_query)
    mock_tc_cls.is_deleted = MagicMock()

    with patch("app.shared.ai.client.AIClient.get_instance") as get_instance:
        client = MagicMock()
        client.chat_completion_json = AsyncMock(return_value=mock_raw)
        get_instance.return_value = client

        with patch("app.modules.test_specs.repository.models.test_case.TestCaseDoc", mock_tc_cls):
            from app.modules.system_config.api.ai_routes import RecommendCasesRequest, recommend_cases
            req = RecommendCasesRequest(change_description="test")
            response = await recommend_cases(req)

    ids = [r.case_id for r in response.data.recommended]
    assert ids == ["TC-A", "TC-B", "TC-C"]
