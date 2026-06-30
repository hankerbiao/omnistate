"""失效分析 API 路由。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.modules.failure_analysis.api.dependencies import FailureAnalysisServiceDep
from app.modules.failure_analysis.schemas.failure_analysis import (
    FailureAnalysisDashboard,
)
from app.shared.ai.client import AIClient
from app.shared.ai.prompts import (
    FAILURE_ANALYSIS_SYSTEM_PROMPT,
    FAILURE_ANALYSIS_USER_TEMPLATE,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission
from app.shared.core.logger import log

router = APIRouter(prefix="/failure-analysis", tags=["Failure Analysis"])


@router.get(
    "/dashboard",
    response_model=APIResponse[FailureAnalysisDashboard],
    summary="获取失效分析仪表盘数据",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def get_failure_analysis_dashboard(
    time_range: str = Query("30d", pattern="^(7d|30d|90d)$"),
    limit_flaky: int = Query(20, ge=1, le=100),
    limit_high_freq: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    service: FailureAnalysisServiceDep = None,
):
    """获取失效分析仪表盘数据。

    - time_range: 时间范围，7d/30d/90d，默认30d
    - limit_flaky: 不稳定测试返回数量上限
    - limit_high_freq: 高频失败返回数量上限
    """
    data = await service.get_dashboard(
        time_range=time_range,
        limit_flaky=limit_flaky,
        limit_high_freq=limit_high_freq,
    )
    return APIResponse(data=data)


# ═══════════════════════════════════════════════════════════════════════
#  AI 失败根因分析
# ═══════════════════════════════════════════════════════════════════════

class AnalyzeFailureRequest(BaseModel):
    """AI 失败根因分析请求。"""
    task_id: str = Field(..., description="执行任务 ID")
    case_id: str = Field(..., description="用例 ID")
    execution_log: str = Field(default="", description="执行日志")
    failure_info: str = Field(default="", description="失败信息/错误消息")
    env_info: str = Field(default="", description="环境信息")


class AnalyzeFailureResponse(BaseModel):
    """AI 失败根因分析结果。"""
    root_cause_category: str = Field(..., description="code_defect/environment/test_case/test_data/infrastructure/unknown")
    confidence: float = Field(..., description="0-1 置信度")
    analysis: str = Field(..., description="根因分析")
    probable_cause: str = Field(..., description="最可能的直接原因")
    fix_suggestions: list[str] = Field(default_factory=list)
    related_patterns: list[str] = Field(default_factory=list)
    severity: str = Field(default="medium", description="critical/high/medium/low")


@router.post(
    "/analyze",
    response_model=APIResponse[AnalyzeFailureResponse],
    summary="AI 分析执行失败根因",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def analyze_failure(request: AnalyzeFailureRequest):
    """AI 分析测试执行失败的根本原因。

    传入执行日志、用例信息和失败信息，AI 返回根因分类、置信度、
    修复建议和相关历史模式。
    """
    if not request.failure_info and not request.execution_log:
        raise HTTPException(status_code=400, detail="execution_log 或 failure_info 至少提供一个")

    case_title = ""
    steps_json = "[]"

    if request.case_id:
        try:
            from app.modules.test_specs.repository.models.test_case import TestCaseDoc
            doc = await TestCaseDoc.find_one(
                TestCaseDoc.case_id == request.case_id,
                TestCaseDoc.is_deleted == False,  # noqa: E712
            )
            if doc:
                case_title = doc.title or ""
                if doc.steps:
                    steps = []
                    for s in doc.steps:
                        steps.append({
                            "step_id": s.step_id,
                            "name": s.name,
                            "action": s.action,
                            "expected": s.expected,
                        })
                    steps_json = json.dumps(steps, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning("Failed to fetch test case {}: {}", request.case_id, e)

    user_content = FAILURE_ANALYSIS_USER_TEMPLATE.format(
        task_id=request.task_id,
        case_id=request.case_id,
        case_title=case_title or "（未知）",
        steps_json=steps_json,
        execution_log=request.execution_log or "（无日志）",
        failure_info=request.failure_info or "（无明确失败信息）",
        env_info=request.env_info or "（无环境信息）",
    )

    client = AIClient.get_instance()
    try:
        raw = await client.chat_completion_json(
            system_prompt=FAILURE_ANALYSIS_SYSTEM_PROMPT,
            user_content=user_content,
            temperature=0.3,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except json.JSONDecodeError as e:
        log.error("AI failure-analysis JSON parse failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 返回格式错误: {e}")
    except Exception as e:
        log.error("AI failure-analysis failed: {}", e)
        raise HTTPException(status_code=502, detail=f"AI 调用失败: {e}")

    result = AnalyzeFailureResponse(
        root_cause_category=str(raw.get("root_cause_category", "unknown")),
        confidence=float(raw.get("confidence", 0.5)),
        analysis=str(raw.get("analysis", "")),
        probable_cause=str(raw.get("probable_cause", "")),
        fix_suggestions=[str(s) for s in raw.get("fix_suggestions", [])],
        related_patterns=[str(p) for p in raw.get("related_patterns", [])],
        severity=str(raw.get("severity", "medium")),
    )

    log.info(
        "AI failure-analysis: task={} case={} category={} confidence={:.2f}",
        request.task_id, request.case_id,
        result.root_cause_category, result.confidence,
    )
    return APIResponse(data=result)
