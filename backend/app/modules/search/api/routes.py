"""全局搜索 API 路由。"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.modules.search.schemas import SearchResponse
from app.modules.search.service import SearchService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "",
    response_model=APIResponse[SearchResponse],
    summary="全局搜索",
)
async def global_search(
    q: str = Query(..., min_length=1, max_length=200, description="搜索关键词"),
    types: Optional[str] = Query(
        None, description="限定搜索范围，逗号分隔，如: requirement,test_case"
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
):
    """全局搜索。

    跨模块搜索测试需求、测试用例、自动化用例、执行任务、评论等。
    结果按类型分组，每组内按更新时间降序排列。
    """
    service = SearchService()
    type_list: Optional[List[str]] = (
        [t.strip() for t in types.split(",")] if types else None
    )
    data = await service.search(query=q, types=type_list, limit=limit, offset=offset)
    return APIResponse(data=data)
