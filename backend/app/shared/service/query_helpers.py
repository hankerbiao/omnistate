"""
共享查询辅助函数

提供软删除查询、文档转换等通用静态方法，减少各 Service 的重复代码。
"""

from datetime import datetime, timezone
from typing import Any


def not_deleted() -> dict[str, bool]:
    """返回软删除感知查询的条件表达式。"""
    return {"is_deleted": False}


def soft_delete(doc: Any) -> None:
    """将文档标记为软删除并更新时间戳。

    Args:
        doc: 支持 is_deleted / deleted_at / update_timestamp 属性的文档对象。
    """
    doc.is_deleted = True
    if hasattr(doc, "deleted_at"):
        doc.deleted_at = datetime.now(timezone.utc)
    if hasattr(doc, "update_timestamp"):
        doc.update_timestamp()


def model_to_public_dict(doc: Any) -> dict[str, Any]:
    """将文档转换为字典并规范化 id 字段为字符串。

    Args:
        doc: Beanie Document 实例。

    Returns:
        包含字符串 id 的字典。
    """
    data = doc.model_dump()
    data["id"] = str(doc.id)
    return data
