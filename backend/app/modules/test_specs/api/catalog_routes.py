"""Catalog API routes (labs, suggestions, tree)."""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.test_specs.api.dependencies import CatalogServiceDep, LabServiceDep
from app.modules.test_specs.domain.exceptions import LabConflictError, LabNotFoundError
from app.modules.test_specs.schemas.catalog import (
    CatalogSuggestionsResponse,
    CatalogTreeResponse,
    CreateLabRequest,
    DeactivateLabRequest,
    LabResponse,
    UpdateLabRequest,
)
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import require_permission

router = APIRouter(prefix="/catalog", tags=["Catalog"])
labs_router = APIRouter(prefix="/labs", tags=["Catalog"])


@labs_router.get(
    "",
    response_model=APIResponse[List[LabResponse]],
    summary="Lab 列表",
    dependencies=[Depends(require_permission("catalog:labs:read"))],
)
async def list_labs(
    lab_service: LabServiceDep,
    active_only: bool = Query(False, description="仅返回启用的 Lab"),
):
    data = await lab_service.list_labs(active_only=active_only)
    return APIResponse(data=data)


@labs_router.post(
    "",
    response_model=APIResponse[LabResponse],
    status_code=201,
    summary="创建 Lab",
    dependencies=[Depends(require_permission("catalog:labs:manage"))],
)
async def create_lab(request: CreateLabRequest, lab_service: LabServiceDep):
    try:
        data = await lab_service.create_lab(request.model_dump())
        return APIResponse(data=data)
    except LabConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@labs_router.put(
    "/{lab_id}",
    response_model=APIResponse[LabResponse],
    summary="更新 Lab（不可改 code）",
    dependencies=[Depends(require_permission("catalog:labs:manage"))],
)
async def update_lab(lab_id: str, request: UpdateLabRequest, lab_service: LabServiceDep):
    try:
        data = await lab_service.update_lab(
            lab_id,
            request.model_dump(exclude_unset=True),
        )
        return APIResponse(data=data)
    except LabNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@labs_router.post(
    "/{lab_id}/deactivate",
    response_model=APIResponse[LabResponse],
    summary="停用 Lab 并迁移用例",
    dependencies=[Depends(require_permission("catalog:labs:manage"))],
)
async def deactivate_lab(
    lab_id: str,
    request: DeactivateLabRequest,
    lab_service: LabServiceDep,
):
    try:
        data = await lab_service.deactivate_lab(lab_id, request.target_lab_id)
        return APIResponse(data=data)
    except LabNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LabConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@labs_router.delete(
    "/{lab_id}",
    status_code=204,
    summary="删除 Lab（仅 0 用例）",
    dependencies=[Depends(require_permission("catalog:labs:manage"))],
)
async def delete_lab(lab_id: str, lab_service: LabServiceDep):
    try:
        await lab_service.delete_lab(lab_id)
    except LabNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LabConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/suggestions",
    response_model=APIResponse[CatalogSuggestionsResponse],
    summary="目录段建议（Creatable）",
    dependencies=[Depends(require_permission("test_cases:read"))],
)
async def catalog_suggestions(
    catalog_service: CatalogServiceDep,
    lab_id: str = Query(...),
    parent_path: str | None = Query(None, description="JSON 数组，父路径"),
):
    try:
        parsed_parent: list[str] = json.loads(parent_path) if parent_path else []
        if not isinstance(parsed_parent, list):
            raise ValueError("parent_path 必须是 JSON 数组")
        segments = await catalog_service.get_suggestions(lab_id, parsed_parent)
        return APIResponse(
            data={
                "lab_id": lab_id,
                "parent_path": parsed_parent,
                "segments": segments,
            }
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LabNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/tree",
    response_model=APIResponse[CatalogTreeResponse],
    summary="Lab 目录树",
    dependencies=[Depends(require_permission("test_cases:read"))],
)
async def catalog_tree(
    catalog_service: CatalogServiceDep,
    lab_id: str = Query(...),
):
    try:
        data = await catalog_service.build_tree(lab_id)
        return APIResponse(data=data)
    except LabNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


router.include_router(labs_router)
