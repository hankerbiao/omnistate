"""
系统配置 API 路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.system_config.schemas import (
    SystemConfigListResponse,
    SystemConfigResponse,
    SystemConfigUpdate,
    BatchUpdateRequest,
    BatchUpdateResponse,
    TestConnectionRequest,
    TestConnectionResponse,
    ConfigHistoryResponse,
)
from app.modules.system_config.service import ConfigService, ConfigValidator
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user

router = APIRouter(prefix="/system-configs", tags=["SystemConfig"])


def _doc_to_response(doc) -> SystemConfigResponse:
    """将文档转换为响应格式"""
    return SystemConfigResponse(
        id=str(doc.id),
        config_key=doc.config_key,
        config_value=doc.config_value,
        config_type=doc.config_type,
        category=doc.category,
        description=doc.description,
        is_encrypted=doc.is_encrypted,
        is_active=doc.is_active,
        needs_restart=ConfigService.get_needs_restart(doc.config_key),
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        updated_by=doc.updated_by,
    )


@router.get("", response_model=APIResponse[SystemConfigListResponse])
async def get_configs(
    category: Optional[str] = Query(None, description="配置分类"),
    active_only: bool = Query(True, description="是否只返回激活的配置"),
    search: Optional[str] = Query(None, description="搜索关键词"),
) -> APIResponse[SystemConfigListResponse]:
    """获取配置列表"""
    docs, total = await ConfigService.get_configs(
        category=category,
        active_only=active_only,
        search=search,
    )
    items = [_doc_to_response(doc) for doc in docs]
    return APIResponse(data=SystemConfigListResponse(items=items, total=total))


@router.get("/categories", response_model=APIResponse[list[str]])
async def get_categories() -> APIResponse[list[str]]:
    """获取配置分类列表"""
    categories = await ConfigService.get_categories()
    return APIResponse(data=categories)


@router.get("/history", response_model=APIResponse[list[ConfigHistoryResponse]])
async def get_config_history(
    config_key: Optional[str] = Query(None, description="配置键（可选，筛选特定配置的历史）"),
    limit: int = Query(50, ge=1, le=200, description="返回数量"),
) -> APIResponse[list[ConfigHistoryResponse]]:
    """获取配置历史记录"""
    docs = await ConfigService.get_history(config_key=config_key, limit=limit)
    items = [
        ConfigHistoryResponse(
            id=str(doc.id),
            config_key=doc.config_key,
            old_value=doc.old_value,
            new_value=doc.new_value,
            changed_by=doc.changed_by,
            changed_at=doc.changed_at,
            remark=doc.remark,
        )
        for doc in docs
    ]
    return APIResponse(data=items)


@router.get("/{config_key}", response_model=APIResponse[SystemConfigResponse])
async def get_config(config_key: str) -> APIResponse[SystemConfigResponse]:
    """获取单个配置"""
    doc = await ConfigService.get_config_by_key(config_key)
    if not doc:
        raise HTTPException(status_code=404, detail=f"配置项不存在: {config_key}")
    return APIResponse(data=_doc_to_response(doc))


@router.put("/{config_key}", response_model=APIResponse[SystemConfigResponse])
async def update_config(
    config_key: str,
    data: SystemConfigUpdate,
    current_user=Depends(get_current_user),
) -> APIResponse[SystemConfigResponse]:
    """更新配置"""
    # 验证配置值
    is_valid, error_msg = ConfigValidator.validate(config_key, data.config_value)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # 更新配置
    doc = await ConfigService.set_config(
        key=config_key,
        value=data.config_value,
        changed_by=current_user.get("username"),
        remark=data.remark,
    )
    return APIResponse(data=_doc_to_response(doc), message="配置更新成功")


@router.put("/batch", response_model=APIResponse[BatchUpdateResponse])
async def batch_update_configs(
    data: BatchUpdateRequest,
    current_user=Depends(get_current_user),
) -> APIResponse[BatchUpdateResponse]:
    """批量更新配置"""
    items = [{"config_key": item.config_key, "config_value": item.config_value} for item in data.items]
    updated_count = await ConfigService.batch_update(
        items=items,
        changed_by=current_user.get("username"),
        remark=data.remark,
    )
    return APIResponse(
        data=BatchUpdateResponse(updated_count=updated_count),
        message="批量更新成功",
    )


@router.post("/ai/test-connection", response_model=APIResponse[TestConnectionResponse])
async def test_ai_connection(data: TestConnectionRequest) -> APIResponse[TestConnectionResponse]:
    """测试AI服务连接"""
    result = await ConfigService.test_ai_connection(
        base_url=data.base_url,
        model=data.model,
        api_key=data.api_key,
        timeout=data.timeout,
    )

    response = TestConnectionResponse(
        success=result["success"],
        model=result.get("model"),
        response_time_ms=result.get("response_time_ms"),
        error=result.get("error"),
    )

    message = "连接成功" if result["success"] else f"连接失败: {result.get('error', '未知错误')}"
    return APIResponse(data=response, message=message)


@router.post("/reload", response_model=APIResponse)
async def reload_config(
    config_key: Optional[str] = Query(None, description="配置键（可选，不传则清除所有缓存）"),
) -> APIResponse:
    """热加载配置（清除缓存）"""
    await ConfigService.reload_config(key=config_key)
    return APIResponse(message="缓存已清除")
