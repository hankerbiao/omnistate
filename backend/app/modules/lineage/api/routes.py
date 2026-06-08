"""测试血缘图谱 API 路由。"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.lineage.api.dependencies import LineageServiceDep
from app.modules.lineage.schemas.lineage import LineageGraphResponse
from app.shared.api.schemas.base import APIResponse
from app.shared.auth import get_current_user, require_permission

router = APIRouter(prefix="/lineage", tags=["Lineage"])


@router.get(
    "/graph",
    response_model=APIResponse[LineageGraphResponse],
    summary="获取测试血缘图谱",
    dependencies=[Depends(require_permission("execution_tasks:read"))],
)
async def get_lineage_graph(
    entity_type: str = Query(
        ...,
        description="Entity type: task|case_result|test_case|requirement|auto_case",
    ),
    entity_id: str = Query(..., description="Entity ID"),
    max_nodes: int = Query(50, ge=1, le=200, description="Max number of nodes"),
    current_user=Depends(get_current_user),
    service: LineageServiceDep = None,
):
    """获取测试血缘图谱。

    从任意实体出发，沿着外键链向上游（需求方向）和下游（Agent方向）
    遍历，构造完整的 DAG 血缘图。

    Args:
        entity_type: 实体类型
        entity_id: 实体 ID
        max_nodes: 最大节点数
        current_user: 当前用户
        service: 血缘图谱服务实例

    Returns:
        包含节点和边的图谱数据

    Raises:
        404: 入口实体不存在时
        400: 不支持的实体类型时
    """
    try:
        data = await service.get_lineage_graph(
            entity_type=entity_type,
            entity_id=entity_id,
            max_nodes=max_nodes,
        )
        return APIResponse(data=data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
