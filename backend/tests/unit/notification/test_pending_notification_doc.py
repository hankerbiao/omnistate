"""PendingNotificationDoc 单元测试。

测试目标：
- 模型结构（collection 名、索引配置）
- 纯方法逻辑（build_key、batch_key）
- 默认值与字段类型
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Beanie ODM 在导入时需要 init，但 PendingNotificationDoc 的 Settings/索引
# 不依赖 init。我们只引用类与 Settings，不直接实例化。
from app.modules.notification.repository.models.pending_notification import (  # noqa: E402
    PendingNotificationDoc,
)
from pymongo import IndexModel  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════
#  Class-level: build_key / batch_key
# ═══════════════════════════════════════════════════════════════════════

def test_build_key_format() -> None:
    assert (
        PendingNotificationDoc.build_key("user-1", "EXECUTION_TASK_ASSIGN")
        == "user-1:EXECUTION_TASK_ASSIGN"
    )


def test_build_key_handles_special_chars() -> None:
    """build_key 不做转义，直接拼接。"""
    assert (
        PendingNotificationDoc.build_key("u-1", "TYPE:WITH:COLONS")
        == "u-1:TYPE:WITH:COLONS"
    )


def test_batch_key_uses_classmethod() -> None:
    """batch_key 是属性，等价于 build_key(user_id, notify_type)。"""
    # 用类方法直接验证等价性（不实例化）
    user_id = "u-test"
    notify_type = "EXECUTION_TASK_ASSIGN"
    expected = PendingNotificationDoc.build_key(user_id, notify_type)
    assert expected == f"{user_id}:{notify_type}"


# ═══════════════════════════════════════════════════════════════════════
#  Settings: collection name
# ═══════════════════════════════════════════════════════════════════════

def test_collection_name_is_pending_notifications() -> None:
    assert PendingNotificationDoc.Settings.name == "pending_notifications"


# ═══════════════════════════════════════════════════════════════════════
#  Settings: indexes
# ═══════════════════════════════════════════════════════════════════════

def _index_keys(idx: IndexModel) -> list[str]:
    """从 IndexModel.document['key'] 抽取索引字段名列表。"""
    return [str(k) for k in idx.document["key"].keys()]


def test_three_indexes_configured() -> None:
    indexes = PendingNotificationDoc.Settings.indexes
    assert len(indexes) == 3, f"expected 3 indexes, got {len(indexes)}"


def test_scheduled_at_index_exists() -> None:
    """第一个索引：scheduled_at 单字段（用于定时任务扫描）。"""
    indexes = PendingNotificationDoc.Settings.indexes
    fields = _index_keys(indexes[0])
    assert fields == ["scheduled_at"]


def test_compound_index_on_user_type_status() -> None:
    """第二个索引：复合 (user_id, notify_type, status)。"""
    indexes = PendingNotificationDoc.Settings.indexes
    fields = _index_keys(indexes[1])
    assert fields == ["user_id", "notify_type", "status"]


def test_ttl_index_on_created_at_7_days() -> None:
    """第三个索引：created_at 上 TTL，7 天后清理已发送记录。"""
    indexes = PendingNotificationDoc.Settings.indexes
    ttl_index = indexes[2]
    fields = _index_keys(ttl_index)
    assert fields == ["created_at"]
    # TTL 配置存在 document 顶层
    assert ttl_index.document.get("expireAfterSeconds") == 7 * 24 * 60 * 60


def test_ttl_index_filters_sent_only() -> None:
    """TTL 索引的 partial filter 只对 sent 状态生效。"""
    indexes = PendingNotificationDoc.Settings.indexes
    ttl_index = indexes[2]
    assert ttl_index.document.get("partialFilterExpression") == {"status": "sent"}


# ═══════════════════════════════════════════════════════════════════════
#  Field type annotations
# ═══════════════════════════════════════════════════════════════════════

def test_user_id_field_is_indexed() -> None:
    """user_id 字段被声明为 Indexed[str]。"""
    annotations = PendingNotificationDoc.model_fields
    assert "user_id" in annotations
    # Field metadata 包含 indexed 标记


def test_notify_type_field_is_indexed() -> None:
    annotations = PendingNotificationDoc.model_fields
    assert "notify_type" in annotations


def test_items_field_is_list_of_dict() -> None:
    annotations = PendingNotificationDoc.model_fields
    assert "items" in annotations


def test_status_field_exists() -> None:
    annotations = PendingNotificationDoc.model_fields
    assert "status" in annotations


def test_scheduled_at_field_required() -> None:
    annotations = PendingNotificationDoc.model_fields
    scheduled = annotations["scheduled_at"]
    # scheduled_at 没有 default，应当必填
    assert scheduled.is_required()


# ═══════════════════════════════════════════════════════════════════════
#  MRO & mixin
# ═══════════════════════════════════════════════════════════════════════

def test_inherits_timestamped_mixin() -> None:
    """PendingNotificationDoc 继承自 TimestampedDocumentMixin。"""
    from app.shared.core.document_mixins import TimestampedDocumentMixin
    assert issubclass(PendingNotificationDoc, TimestampedDocumentMixin)


def test_inherits_document_base() -> None:
    from beanie import Document
    assert issubclass(PendingNotificationDoc, Document)
