"""Global metadata dictionary API."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.test_specs.schemas import (
    CreateTestCaseMetadataRequest,
    MetadataTypesResponse,
    TestCaseMetadataResponse,
    UpdateTestCaseMetadataRequest,
)
from app.modules.test_specs.service import MetadataService
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/metadata", tags=["Metadata"])


@router.get("/types", response_model=APIResponse[MetadataTypesResponse], dependencies=[Depends(require_permission("test_cases:read"))])
async def list_metadata_types():
    return APIResponse(data=await MetadataService.list_types())


@router.get("", response_model=APIResponse[dict], dependencies=[Depends(require_permission("metadata:manage"))])
async def list_metadata(
    type_code: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return APIResponse(data=await MetadataService.list_admin(type_code, active, q, limit, offset))


@router.post("", response_model=APIResponse[TestCaseMetadataResponse], status_code=201, dependencies=[Depends(require_permission("metadata:manage"))])
async def create_metadata(request: CreateTestCaseMetadataRequest, current_user=Depends(get_current_user)):
    try:
        return APIResponse(data=await MetadataService.create(request.model_dump(), str(current_user.get("user_id"))))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{metadata_id}", response_model=APIResponse[TestCaseMetadataResponse], dependencies=[Depends(require_permission("metadata:manage"))])
async def update_metadata(metadata_id: str, request: UpdateTestCaseMetadataRequest, current_user=Depends(get_current_user)):
    try:
        data = await MetadataService.update(metadata_id, request.model_dump(exclude_unset=True), str(current_user.get("user_id")))
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{metadata_id}/deactivate", response_model=APIResponse[TestCaseMetadataResponse], dependencies=[Depends(require_permission("metadata:manage"))])
async def deactivate_metadata(metadata_id: str, current_user=Depends(get_current_user)):
    try:
        data = await MetadataService.deactivate(metadata_id, str(current_user.get("user_id")))
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
