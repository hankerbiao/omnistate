"""测试用例评论 API 路由"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.test_specs.schemas.comment import (
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
    UpdateCommentRequest,
)
from app.modules.test_specs.service.comment_service import TestCaseCommentService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/test-cases/{case_id}/comments", tags=["TestCases"])


def get_comment_service() -> TestCaseCommentService:
    return TestCaseCommentService()


CommentServiceDep = Annotated[TestCaseCommentService, Depends(get_comment_service)]


@router.get(
    "",
    response_model=APIResponse[CommentListResponse],
    summary="获取测试用例评论列表",
    dependencies=[Depends(require_permission("test_cases:read"))],
)
async def list_comments(
    case_id: str,
    comment_service: CommentServiceDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    docs, total = await comment_service.list_comments(case_id, limit=limit, offset=offset)
    items = [CommentResponse(**doc.model_dump(by_alias=True), _id=str(doc.id)) for doc in docs]
    return APIResponse(data=CommentListResponse(items=items, total=total))


@router.post(
    "",
    response_model=APIResponse[CommentResponse],
    status_code=201,
    summary="创建测试用例评论",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def create_comment(
    case_id: str,
    request: CreateCommentRequest,
    comment_service: CommentServiceDep,
    current_user: dict = Depends(get_current_user),
):
    doc = await comment_service.create_comment(
        case_id=case_id,
        content=request.content,
        author_id=str(current_user["user_id"]),
        author_name=current_user.get("username"),
    )
    return APIResponse(
        data=CommentResponse(**doc.model_dump(by_alias=True), _id=str(doc.id))
    )


@router.put(
    "/{comment_id}",
    response_model=APIResponse[CommentResponse],
    summary="编辑测试用例评论",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def update_comment(
    case_id: str,
    comment_id: str,
    request: UpdateCommentRequest,
    comment_service: CommentServiceDep,
    current_user: dict = Depends(get_current_user),
):
    doc = await comment_service.update_comment(
        comment_id=comment_id,
        content=request.content,
        actor_id=str(current_user["user_id"]),
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="comment not found or not owned by you")
    return APIResponse(
        data=CommentResponse(**doc.model_dump(by_alias=True), _id=str(doc.id))
    )


@router.delete(
    "/{comment_id}",
    status_code=204,
    summary="删除测试用例评论",
    dependencies=[Depends(require_permission("test_cases:write"))],
)
async def delete_comment(
    case_id: str,
    comment_id: str,
    comment_service: CommentServiceDep,
    current_user: dict = Depends(get_current_user),
):
    ok = await comment_service.delete_comment(
        comment_id=comment_id,
        actor_id=str(current_user["user_id"]),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="comment not found or not owned by you")
