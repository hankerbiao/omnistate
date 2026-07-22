"""用例集合 API 路由。"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.modules.test_case_collection.api.dependencies import CollectionServiceDep
from app.modules.test_case_collection.schemas import (
    AddCasesRequest,
    CollectionChangeLogListResponse,
    CollectionListItem,
    CollectionResponse,
    CollectionValiditySummary,
    CopyCollectionRequest,
    CreateCollectionRequest,
    RemoveCasesRequest,
    UpdateCollectionRequest,
)
from app.modules.test_case_collection.service.exceptions import (
    CollectionNotFoundError,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter(prefix="/collections", tags=["TestCaseCollection"])


@router.post(
    "",
    response_model=APIResponse[CollectionResponse],
    status_code=201,
    summary="创建用例集合",
)
async def create_collection(
    request: CreateCollectionRequest,
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
):
    """创建用例集合。"""
    data = await service.create(request, creator_id=current_user["user_id"], current_user=current_user)
    return APIResponse(data=data)


@router.get(
    "",
    response_model=APIResponse[list[CollectionListItem]],
    summary="查询用例集合列表",
)
async def list_collections(
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
    q: str = Query(None, description="模糊搜索名称/描述/标签"),
):
    """查询用例集合列表，支持模糊搜索。"""
    data = await service.list_all(query=q)
    return APIResponse(data=data)


@router.get(
    "/search",
    response_model=APIResponse[list[CollectionListItem]],
    summary="快速搜索用例集合（用于任务创建下拉）",
)
async def search_collections(
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50),
):
    """快速搜索集合。按名称和标签匹配，用于任务创建时快速选择。"""
    data = await service.search(q, limit=limit)
    return APIResponse(data=data)


@router.get(
    "/{collection_id}",
    response_model=APIResponse[CollectionResponse],
    summary="获取用例集合详情",
)
async def get_collection(
    collection_id: str,
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
):
    """获取用例集合详情。"""
    try:
        data = await service.get(collection_id)
        return APIResponse(data=data)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{collection_id}/copy",
    response_model=APIResponse[CollectionResponse],
    status_code=201,
    summary="另存为用例集合",
)
async def copy_collection(
    collection_id: str,
    request: CopyCollectionRequest,
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
):
    """基于已有集合另存为新集合。"""
    try:
        data = await service.copy(collection_id, request, current_user)
        return APIResponse(data=data)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/{collection_id}/history",
    response_model=APIResponse[CollectionChangeLogListResponse],
    summary="获取集合变更历史",
)
async def get_collection_history(
    collection_id: str,
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """按时间倒序获取集合变更历史。"""
    try:
        data = await service.history(collection_id, limit=limit, offset=offset)
        return APIResponse(data=data)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/{collection_id}/validity",
    response_model=APIResponse[CollectionValiditySummary],
    summary="获取集合用例有效性",
)
async def get_collection_validity(
    collection_id: str,
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
):
    """获取集合内用例有效性风险汇总。"""
    try:
        data = await service.validity(collection_id)
        return APIResponse(data=data)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/{collection_id}/export",
    summary="导出集合用例清单",
)
async def export_collection(
    collection_id: str,
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
):
    """导出集合用例清单，支持 CSV/XLSX。"""
    try:
        content, media_type, filename = await service.export_cases(collection_id, format, current_user)
        quoted_filename = quote(filename)
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}"},
        )
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put(
    "/{collection_id}",
    response_model=APIResponse[CollectionResponse],
    summary="更新用例集合基本信息",
)
async def update_collection(
    collection_id: str,
    request: UpdateCollectionRequest,
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
):
    """更新集合名称/描述/标签。"""
    try:
        data = await service.update(collection_id, request, current_user)
        return APIResponse(data=data)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete(
    "/{collection_id}",
    response_model=APIResponse[dict],
    summary="删除用例集合",
)
async def delete_collection(
    collection_id: str,
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
):
    """删除用例集合（逻辑删除）。仅 Admin 或创建者可删除。"""
    try:
        await service.delete(collection_id, current_user)
        return APIResponse(data={"deleted": collection_id})
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{collection_id}/cases",
    response_model=APIResponse[CollectionResponse],
    summary="向集合添加用例",
)
async def add_cases_to_collection(
    collection_id: str,
    request: AddCasesRequest,
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
):
    """批量向集合添加用例（自动去重）。"""
    try:
        data = await service.add_cases(collection_id, request, current_user)
        return APIResponse(data=data)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete(
    "/{collection_id}/cases",
    response_model=APIResponse[CollectionResponse],
    summary="从集合移除用例",
)
async def remove_cases_from_collection(
    collection_id: str,
    request: RemoveCasesRequest,
    service: CollectionServiceDep,
    current_user=Depends(get_current_user),
):
    """批量从集合移除用例。"""
    try:
        data = await service.remove_cases(collection_id, request, current_user)
        return APIResponse(data=data)
    except CollectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
