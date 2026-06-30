"""AI 辅助工具路由（润色、步骤分析等）"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.modules.system_config.constants.ai import POLISH_SYSTEM_PROMPT
from app.shared.ai.client import AIClient
from app.shared.ai.prompts import (
    GENERATE_CASES_SYSTEM_PROMPT,
    GENERATE_CASES_USER_TEMPLATE,
    RECOMMEND_CASES_SYSTEM_PROMPT,
    RECOMMEND_CASES_USER_TEMPLATE,
    REVIEW_CASE_SYSTEM_PROMPT,
    REVIEW_CASE_USER_TEMPLATE,
    STEP_ANALYSIS_SYSTEM_PROMPT,
    STEP_ANALYSIS_USER_TEMPLATE,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.core.logger import log

router = APIRouter(prefix="/ai", tags=["AI Tools"])


# ═══════════════════════════════════════════════════════════════════════
#  文本润色
# ═══════════════════════════════════════════════════════════════════════

class PolishRequest(BaseModel):
    text: str


class PolishResponse(BaseModel):
    polished: str


@router.post("/polish", response_model=APIResponse[PolishResponse])
async def polish_text(request: PolishRequest):
    """使用配置的 AI 模型润色文本"""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")

    client = AIClient.get_instance()
    try:
        polished = await client.simple_chat(
            system_prompt=POLISH_SYSTEM_PROMPT,
            user_content=text,
            temperature=0.3,
        )
        log.info("AI polish: {} chars -> {} chars", len(text), len(polished))
        return APIResponse(data=PolishResponse(polished=polished.strip()))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.error("AI polish failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 调用失败: {e}")


# ═══════════════════════════════════════════════════════════════════════
#  测试用例步骤分析
# ═══════════════════════════════════════════════════════════════════════

class AnalyzeStepsRequest(BaseModel):
    """步骤分析请求体，与前端 AnalyzeTestStepsRequest 对齐。"""
    steps: list[dict[str, Any]] = Field(..., description="测试用例步骤列表")
    title: str = Field(default="", description="用例标题")
    category: str = Field(default="", description="用例分类")
    pre_condition: str = Field(default="", description="前置条件")
    post_condition: str = Field(default="", description="后置条件")


class StepAnalysisIssue(BaseModel):
    """单个步骤问题，与前端 StepAnalysisIssue 对齐。"""
    stepIndex: int = Field(..., description="0-based 步骤索引")
    severity: str = Field(..., description="error / warning / suggestion")
    category: str = Field(default="completeness", description="问题分类")
    field: str | None = Field(default=None, description="name / action / expected")
    message: str = Field(..., description="问题描述")
    proposedValue: str | None = Field(default=None, description="建议值")


class StepAnalysisResult(BaseModel):
    """步骤分析结果，与前端 StepAnalysisResult 对齐。"""
    score: int = Field(..., description="0-100 评分")
    totalSteps: int = Field(..., description="步骤总数")
    issues: list[StepAnalysisIssue] = Field(default_factory=list)
    summary: str = Field(default="", description="整体评价")


@router.post("/analyze-steps", response_model=APIResponse[StepAnalysisResult])
async def analyze_test_steps(request: AnalyzeStepsRequest):
    """AI 分析测试用例步骤的完整性和质量。

    前端 TestCaseStepEditorV2 组件调用此端点，传入用例步骤数据，
    返回评分 + 问题列表 + 整体评价。
    """
    if not request.steps:
        raise HTTPException(status_code=400, detail="steps 不能为空")

    steps_json = json.dumps(request.steps, ensure_ascii=False, indent=2)
    user_content = STEP_ANALYSIS_USER_TEMPLATE.format(
        title=request.title or "（未提供标题）",
        category=request.category or "（未提供）",
        pre_condition=request.pre_condition or "（无）",
        post_condition=request.post_condition or "（无）",
        step_count=len(request.steps),
        steps_json=steps_json,
    )

    client = AIClient.get_instance()
    try:
        raw = await client.chat_completion_json(
            system_prompt=STEP_ANALYSIS_SYSTEM_PROMPT,
            user_content=user_content,
            temperature=0.2,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except json.JSONDecodeError as e:
        log.error("AI analyze-steps JSON parse failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 返回格式错误: {e}")
    except Exception as e:
        log.error("AI analyze-steps failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 调用失败: {e}")

    score = int(raw.get("score", 0))
    total_steps = int(raw.get("totalSteps", len(request.steps)))
    summary = str(raw.get("summary", ""))

    issues: list[StepAnalysisIssue] = []
    for item in raw.get("issues", []):
        issues.append(StepAnalysisIssue(
            stepIndex=int(item.get("stepIndex", 0)),
            severity=str(item.get("severity", "suggestion")),
            category=str(item.get("category", "completeness")),
            field=item.get("field"),
            message=str(item.get("message", "")),
            proposedValue=item.get("proposedValue"),
        ))

    result = StepAnalysisResult(
        score=score,
        totalSteps=total_steps,
        issues=issues,
        summary=summary,
    )

    log.info(
        "AI analyze-steps: steps={} score={} issues={}",
        len(request.steps), score, len(issues),
    )
    return APIResponse(data=result)


# ═══════════════════════════════════════════════════════════════════════
#  需求→用例生成
# ═══════════════════════════════════════════════════════════════════════

class GeneratedCaseStep(BaseModel):
    """AI 生成的用例步骤。"""
    step_id: str = Field(..., description="步骤 ID")
    name: str = Field(..., description="步骤简述")
    action: str = Field(..., description="具体操作步骤")
    expected: str = Field(..., description="预期结果")


class GeneratedCaseDraft(BaseModel):
    """AI 生成的单条用例草稿。"""
    title: str = Field(..., description="用例标题")
    priority: str = Field(default="P2", description="P0/P1/P2/P3")
    test_category: str = Field(default="functional", description="测试分类")
    pre_condition: str = Field(default="", description="前置条件")
    post_condition: str = Field(default="", description="后置条件")
    steps: list[GeneratedCaseStep] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rationale: str = Field(default="", description="生成此用例的理由")


class GenerateCasesResponse(BaseModel):
    """用例生成响应。"""
    cases: list[GeneratedCaseDraft] = Field(default_factory=list)
    reason: str = Field(default="", description="如果未生成用例，说明原因")


class GenerateCasesRequest(BaseModel):
    """用例生成请求。

    两种模式：
    - 传 requirement_id：从数据库读取需求信息
    - 传 requirement_text：直接提供需求文本
    """
    requirement_id: str | None = Field(default=None, description="需求 ID（二选一）")
    requirement_text: str | None = Field(default=None, description="需求文本（二选一）")
    max_cases: int = Field(default=5, ge=1, le=20, description="最大生成用例数")


@router.post("/generate-cases", response_model=APIResponse[GenerateCasesResponse])
async def generate_cases(request: GenerateCasesRequest):
    """AI 根据测试需求自动生成测试用例草稿。

    输入需求 ID 或需求文本，AI 生成测试用例草稿列表，
    前端可编辑后批量保存。
    """
    if not request.requirement_id and not request.requirement_text:
        raise HTTPException(status_code=400, detail="requirement_id 或 requirement_text 至少提供一个")

    title = ""
    priority = "P1"
    category = ""
    description = ""
    acceptance_criteria = ""
    key_parameters = ""
    risk_points = ""

    if request.requirement_id:
        from app.modules.test_specs.repository.models.requirement import TestRequirementDoc
        doc = await TestRequirementDoc.find_one(
            TestRequirementDoc.req_id == request.requirement_id,
            TestRequirementDoc.is_deleted == False,  # noqa: E712
        )
        if not doc:
            raise HTTPException(status_code=404, detail=f"需求不存在: {request.requirement_id}")
        title = doc.title or ""
        priority = doc.priority or "P1"
        category = doc.category or ""
        description = doc.description or ""
        acceptance_criteria = doc.acceptance_criteria or ""
        if doc.key_parameters:
            key_parameters = json.dumps(doc.key_parameters, ensure_ascii=False, indent=2)
        risk_points = doc.risk_points or ""
    else:
        description = request.requirement_text or ""
        title = "（用户提供的文本需求）"

    user_content = GENERATE_CASES_USER_TEMPLATE.format(
        title=title,
        priority=priority,
        category=category or "（未指定）",
        description=description or "（无描述）",
        acceptance_criteria=acceptance_criteria or "（无）",
        key_parameters=key_parameters or "（无）",
        risk_points=risk_points or "（无）",
        max_cases=request.max_cases,
    )

    client = AIClient.get_instance()
    try:
        raw = await client.chat_completion_json(
            system_prompt=GENERATE_CASES_SYSTEM_PROMPT,
            user_content=user_content,
            temperature=0.4,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except json.JSONDecodeError as e:
        log.error("AI generate-cases JSON parse failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 返回格式错误: {e}")
    except Exception as e:
        log.error("AI generate-cases failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 调用失败: {e}")

    cases: list[GeneratedCaseDraft] = []
    for item in raw.get("cases", []):
        steps = []
        for s in item.get("steps", []):
            steps.append(GeneratedCaseStep(
                step_id=str(s.get("step_id", f"step-{len(steps)+1}")),
                name=str(s.get("name", "")),
                action=str(s.get("action", "")),
                expected=str(s.get("expected", "")),
            ))
        cases.append(GeneratedCaseDraft(
            title=str(item.get("title", "")),
            priority=str(item.get("priority", "P2")),
            test_category=str(item.get("test_category", "functional")),
            pre_condition=str(item.get("pre_condition", "")),
            post_condition=str(item.get("post_condition", "")),
            steps=steps,
            tags=[str(t) for t in item.get("tags", [])],
            rationale=str(item.get("rationale", "")),
        ))

    reason = str(raw.get("reason", ""))

    log.info(
        "AI generate-cases: req={} max={} generated={}",
        request.requirement_id or "text", request.max_cases, len(cases),
    )
    return APIResponse(data=GenerateCasesResponse(cases=cases, reason=reason))


# ═══════════════════════════════════════════════════════════════════════
#  用例评审建议
# ═══════════════════════════════════════════════════════════════════════

class ReviewCaseRequest(BaseModel):
    """用例评审请求。"""
    case_id: str = Field(..., description="用例 ID")


class ReviewDimension(BaseModel):
    """单维度评审结果。"""
    score: int = Field(..., description="0-100")
    issues: list[str] = Field(default_factory=list)


class ReviewCaseResponse(BaseModel):
    """用例评审结果。"""
    score: int = Field(..., description="0-100 总分")
    verdict: str = Field(..., description="pass / needs_revision / reject")
    dimensions: dict[str, ReviewDimension] = Field(default_factory=dict)
    missing_scenarios: list[str] = Field(default_factory=list)
    priority_suggestion: str = Field(default="保持不变")
    summary: str = Field(default="")


@router.post("/review-case", response_model=APIResponse[ReviewCaseResponse])
async def review_case(request: ReviewCaseRequest):
    """AI 评审单条测试用例。

    从完整性、清晰度、可追溯性、可执行性四个维度评审，
    返回评分 + verdict + 缺失场景 + 优先级建议。
    """
    from app.modules.test_specs.repository.models.test_case import TestCaseDoc

    doc = await TestCaseDoc.find_one(
        TestCaseDoc.case_id == request.case_id,
        TestCaseDoc.is_deleted == False,  # noqa: E712
    )
    if not doc:
        raise HTTPException(status_code=404, detail=f"用例不存在: {request.case_id}")

    steps = []
    for s in (doc.steps or []):
        steps.append({
            "step_id": s.step_id,
            "name": s.name,
            "action": s.action,
            "expected": s.expected,
        })

    user_content = REVIEW_CASE_USER_TEMPLATE.format(
        title=doc.title or "（无标题）",
        case_id=request.case_id,
        priority=doc.priority or "未指定",
        test_category=doc.test_category or "未指定",
        tags=", ".join(doc.tags) if doc.tags else "无",
        pre_condition=doc.pre_condition or "无",
        post_condition=doc.post_condition or "无",
        ref_req_id=doc.ref_req_id or "无",
        step_count=len(steps),
        steps_json=json.dumps(steps, ensure_ascii=False, indent=2),
    )

    client = AIClient.get_instance()
    try:
        raw = await client.chat_completion_json(
            system_prompt=REVIEW_CASE_SYSTEM_PROMPT,
            user_content=user_content,
            temperature=0.3,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except json.JSONDecodeError as e:
        log.error("AI review-case JSON parse failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 返回格式错误: {e}")
    except Exception as e:
        log.error("AI review-case failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 调用失败: {e}")

    dimensions: dict[str, ReviewDimension] = {}
    for dim_name, dim_data in (raw.get("dimensions") or {}).items():
        dimensions[dim_name] = ReviewDimension(
            score=int(dim_data.get("score", 0)),
            issues=[str(i) for i in dim_data.get("issues", [])],
        )

    result = ReviewCaseResponse(
        score=int(raw.get("score", 0)),
        verdict=str(raw.get("verdict", "needs_revision")),
        dimensions=dimensions,
        missing_scenarios=[str(s) for s in raw.get("missing_scenarios", [])],
        priority_suggestion=str(raw.get("priority_suggestion", "保持不变")),
        summary=str(raw.get("summary", "")),
    )

    log.info(
        "AI review-case: case={} score={} verdict={}",
        request.case_id, result.score, result.verdict,
    )
    return APIResponse(data=result)


# ═══════════════════════════════════════════════════════════════════════
#  智能用例选择
# ═══════════════════════════════════════════════════════════════════════

class RecommendCasesRequest(BaseModel):
    """智能用例选择请求。"""
    project_id: str = Field(default="", description="项目 ID")
    change_description: str = Field(..., description="变更描述/commit range")
    case_ids: list[str] = Field(default_factory=list, description="候选用例 ID 列表（可选，留空则查全部）")
    max_recommend: int = Field(default=20, ge=1, le=100, description="最大推荐数")


class RecommendedCase(BaseModel):
    """单条推荐用例。"""
    case_id: str
    reason: str = Field(default="")
    priority_order: int = Field(default=0)


class ExcludedCase(BaseModel):
    """被排除的用例。"""
    case_id: str
    reason: str = Field(default="")


class RecommendCasesResponse(BaseModel):
    """智能用例选择结果。"""
    recommended: list[RecommendedCase] = Field(default_factory=list)
    excluded: list[ExcludedCase] = Field(default_factory=list)
    coverage_note: str = Field(default="")
    estimated_runtime_min: int = Field(default=0)


@router.post("/recommend-cases", response_model=APIResponse[RecommendCasesResponse])
async def recommend_cases(request: RecommendCasesRequest):
    """AI 根据变更范围推荐应执行的测试用例。

    输入变更描述和候选用例列表，AI 返回推荐用例（含理由和优先级顺序）
    以及被排除的用例（含排除理由）。
    """
    from app.modules.test_specs.repository.models.test_case import TestCaseDoc

    if request.case_ids:
        docs = await TestCaseDoc.find(
            TestCaseDoc.case_id.in_(request.case_ids),
            TestCaseDoc.is_deleted == False,  # noqa: E712
        ).to_list()
    else:
        docs = await TestCaseDoc.find(
            TestCaseDoc.is_deleted == False,  # noqa: E712
        ).to_list()

    if not docs:
        raise HTTPException(status_code=404, detail="没有找到候选用例")

    cases_summary = []
    for d in docs[:100]:
        cases_summary.append({
            "case_id": d.case_id,
            "title": d.title,
            "priority": d.priority or "P2",
            "test_category": d.test_category or "",
            "tags": d.tags or [],
        })

    user_content = RECOMMEND_CASES_USER_TEMPLATE.format(
        project_id=request.project_id or "未指定",
        change_description=request.change_description,
        total_cases=len(docs),
        cases_json=json.dumps(cases_summary, ensure_ascii=False, indent=2),
        failure_stats="（暂无历史失败统计，请基于用例信息推荐）",
    )

    client = AIClient.get_instance()
    try:
        raw = await client.chat_completion_json(
            system_prompt=RECOMMEND_CASES_SYSTEM_PROMPT,
            user_content=user_content,
            temperature=0.4,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except json.JSONDecodeError as e:
        log.error("AI recommend-cases JSON parse failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 返回格式错误: {e}")
    except Exception as e:
        log.error("AI recommend-cases failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 调用失败: {e}")

    recommended = []
    for item in raw.get("recommended", [])[:request.max_recommend]:
        recommended.append(RecommendedCase(
            case_id=str(item.get("case_id", "")),
            reason=str(item.get("reason", "")),
            priority_order=int(item.get("priority_order", 0)),
        ))
    recommended.sort(key=lambda x: x.priority_order)

    excluded = []
    for item in raw.get("excluded", []):
        excluded.append(ExcludedCase(
            case_id=str(item.get("case_id", "")),
            reason=str(item.get("reason", "")),
        ))

    result = RecommendCasesResponse(
        recommended=recommended,
        excluded=excluded,
        coverage_note=str(raw.get("coverage_note", "")),
        estimated_runtime_min=int(raw.get("estimated_runtime_min", 0)),
    )

    log.info(
        "AI recommend-cases: project={} candidates={} recommended={} excluded={}",
        request.project_id, len(docs), len(recommended), len(excluded),
    )
    return APIResponse(data=result)
