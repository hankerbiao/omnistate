"""测试血缘图谱数据模型。"""
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field

# --- Node Types ---
NodeType = Literal[
    "requirement",
    "test_case",
    "automation_case",
    "task",
    "case_result",
    "agent",
]


class LineageNode(BaseModel):
    """血缘图谱中的节点。"""

    id: str = Field(..., description="实体唯一 ID")
    type: NodeType = Field(..., description="节点分类")
    label: str = Field(..., description="节点显示名称")
    status: Optional[str] = Field(None, description="状态（用于节点颜色编码）")
    subtitle: Optional[str] = Field(None, description="辅助信息（ID/负责人/主机名）")
    meta: Dict[str, Any] = Field(
        default_factory=dict, description="额外字段，供详情弹窗使用"
    )


class LineageEdge(BaseModel):
    """血缘图谱中的边（关系）。"""

    source: str = Field(..., description="源节点 ID")
    target: str = Field(..., description="目标节点 ID")
    label: str = Field(..., description="关系描述（如：contains, executes, automated_by）")


class LineageGraphResponse(BaseModel):
    """血缘图谱响应。"""

    nodes: List[LineageNode] = Field(default_factory=list, description="所有节点")
    edges: List[LineageEdge] = Field(default_factory=list, description="所有边")
    root_id: str = Field(..., description="用户发起查询的实体 ID")
    root_type: NodeType = Field(..., description="用户发起查询的实体类型")
