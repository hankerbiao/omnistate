"""Embedding API 路由 — 批量重算 + 语义搜索。"""
from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.test_specs.repository.models.test_case import TestCaseDoc
from app.modules.test_specs.repository.models.requirement import TestRequirementDoc
from app.modules.test_specs.service.test_case_service import TestCaseService
from app.modules.test_specs.service.requirement_service import RequirementService
from app.shared.ai.embedding import EmbeddingService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission
from app.shared.core.logger import log

router = APIRouter(prefix="/ai", tags=["AI Embedding"])


@router.post(
    "/re-embed/cases",
    response_model=APIResponse,
    summary="批量重新生成用例的 embedding 向量",
    dependencies=[Depends(require_permission("system:config"))],
)
async def re_embed_all_cases():
    """扫描所有没有 embedding 的用例，异步生成向量。"""
    cases = await TestCaseDoc.find(
        TestCaseDoc.embedding == None, TestCaseDoc.is_deleted == False
    ).to_list()

    count = 0
    for doc in cases:
        # 异步但不等待结果
        import asyncio
        asyncio.create_task(TestCaseService._refresh_embedding(doc))
        count += 1

    log.info("embedding: 已触发 {} 个用例的向量生成", count)
    return APIResponse(data={"triggered": count}, message=f"已触发 {count} 个用例的向量生成")


@router.post(
    "/re-embed/requirements",
    response_model=APIResponse,
    summary="批量重新生成需求的 embedding 向量",
    dependencies=[Depends(require_permission("system:config"))],
)
async def re_embed_all_requirements():
    """扫描所有没有 embedding 的需求，异步生成向量。"""
    reqs = await TestRequirementDoc.find(
        TestRequirementDoc.embedding == None, TestRequirementDoc.is_deleted == False
    ).to_list()

    count = 0
    for doc in reqs:
        import asyncio
        asyncio.create_task(RequirementService._refresh_embedding(doc.req_id, doc))
        count += 1

    log.info("embedding: 已触发 {} 个需求的向量生成", count)
    return APIResponse(data={"triggered": count}, message=f"已触发 {count} 个需求的向量生成")


@router.post(
    "/semantic-search",
    response_model=APIResponse,
    summary="语义搜索用例和需求",
)
async def semantic_search(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    scope: str = Query("all", description="搜索范围: all/cases/requirements"),
):
    """用 embedding 做语义搜索，结果按相似度排序。"""
    if not query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")

    # 把搜索词也转成向量
    vector = await EmbeddingService.embed_text(query.strip())
    if not vector:
        raise HTTPException(status_code=502, detail="Embedding API 不可用")

    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """余弦相似度计算。"""
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na * nb == 0:
            return 0.0
        return dot / (na * nb)

    results: list[dict[str, Any]] = []
    seen = 0

    if scope in ("all", "cases"):
        cases = await TestCaseDoc.find(
            TestCaseDoc.embedding != None, TestCaseDoc.is_deleted == False,
        ).to_list()

        for doc in cases:
            sim = cosine_similarity(vector, doc.embedding)
            if sim > 0.3:  # 相似度阈值
                results.append({
                    "type": "case",
                    "id": doc.case_id,
                    "title": doc.title,
                    "priority": doc.priority,
                    "tags": doc.tags,
                    "score": round(sim, 4),
                })

    if scope in ("all", "requirements"):
        reqs = await TestRequirementDoc.find(
            TestRequirementDoc.embedding != None, TestRequirementDoc.is_deleted == False,
        ).to_list()

        for doc in reqs:
            sim = cosine_similarity(vector, doc.embedding)
            if sim > 0.3:
                results.append({
                    "type": "requirement",
                    "id": doc.req_id,
                    "title": doc.title,
                    "priority": doc.priority,
                    "tags": doc.tags,
                    "score": round(sim, 4),
                })

    # 按相似度从高到低排序
    results.sort(key=lambda r: r["score"], reverse=True)

    log.info(
        "semantic-search: query={} threshold=0.3 found={}",
        query, len(results),
    )
    return APIResponse(data={
        "query": query,
        "results": results[:limit],
        "total": min(len(results), limit),
    })
