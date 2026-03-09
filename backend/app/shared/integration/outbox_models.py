"""发件箱集成模型 - Phase 5

发件箱模式用于将本地数据库事务与外部系统（如Kafka）的集成解耦。
当本地事务提交后，后台工作器负责将outbox事件发布到外部系统，
确保本地状态与外部发布的一致性。

这是Phase 5"基于发件箱的执行调度"的核心实现。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from beanie import Document, before_event, Save, Insert
from pymongo import IndexModel, ASCENDING, DESCENDING


class OutboxEventDoc(Document):
    """发件箱事件文档

    记录需要发布到外部系统的事件，用于实现可靠的事件发布。
    通过发件箱模式确保本地事务提交后，事件最终能够成功发布到外部系统。

    核心字段：
    - event_type: 事件类型（如'execution_task_dispatched'）
    - aggregate_type: 聚合类型（如'ExecutionTask'）
    - aggregate_id: 聚合ID（如task_id）
    - payload: 事件负载数据
    - status: 发布状态（PENDING、SENT、FAILED）
    - retry_count: 重试次数
    - next_retry_at: 下次重试时间
    - last_error: 最后一次错误信息
    """
    __test__ = False

    # 事件标识
    event_id: str = Field(..., description="事件唯一标识（UUID或雪花ID）")

    # 聚合信息
    aggregate_type: str = Field(..., description="聚合类型（ExecutionTask、TestCase等）")
    aggregate_id: str = Field(..., description="聚合ID（task_id、case_id等）")

    # 事件内容
    event_type: str = Field(..., description="事件类型（如execution_task_dispatched）")
    payload: Dict[str, Any] = Field(..., description="事件负载数据")

    # 发布状态
    status: str = Field(default="PENDING", description="发布状态：PENDING、SENT、FAILED、PERMANENTLY_FAILED")
    retry_count: int = Field(default=0, description="重试次数")
    next_retry_at: Optional[datetime] = Field(None, description="下次重试时间")

    # 错误信息
    last_error: Optional[str] = Field(None, description="最后一次错误信息")
    error_history: List[str] = Field(default_factory=list, description="错误历史（最多保存5条）")

    # 时间戳
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="事件创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="事件更新时间")
    sent_at: Optional[datetime] = Field(None, description="成功发布时间")

    @before_event([Save, Insert])
    def update_updated_at(self):
        """自动更新updated_at字段"""
        self.updated_at = datetime.now(timezone.utc)

    def mark_as_sent(self) -> None:
        """标记为已发送"""
        self.status = "SENT"
        self.sent_at = datetime.now(timezone.utc)
        self.next_retry_at = None
        self.last_error = None

    def mark_as_failed(self, error_message: str) -> None:
        """标记为失败并增加重试计数"""
        self.retry_count += 1
        self.last_error = error_message
        self.error_history.append(f"{datetime.now(timezone.utc).isoformat()}: {error_message}")

        # 保持错误历史最多5条
        if len(self.error_history) > 5:
            self.error_history = self.error_history[-5:]

        # 设置状态
        if self.retry_count >= 5:  # 最多重试5次
            self.status = "PERMANENTLY_FAILED"
        else:
            self.status = "FAILED"
            # 指数退避重试策略
            retry_delay_seconds = min(2 ** self.retry_count, 300)  # 最多5分钟
            self.next_retry_at = datetime.now(timezone.utc).timestamp() + retry_delay_seconds

    def can_retry(self) -> bool:
        """检查是否应该重试"""
        if self.status not in ["FAILED", "PENDING"]:
            return False

        if self.status == "PERMANENTLY_FAILED":
            return False

        if self.retry_count >= 5:
            return False

        if self.next_retry_at and datetime.now(timezone.utc) < self.next_retry_at:
            return False

        return True

    class Settings:
        name = "integration_outbox"
        indexes = [
            IndexModel("status"),
            IndexModel("aggregate_type"),
            IndexModel("aggregate_id"),
            IndexModel("event_type"),
            IndexModel("created_at"),
            IndexModel("next_retry_at"),
            IndexModel([("status", ASCENDING), ("created_at", ASCENDING)]),  # 复合索引用于批量查询
        ]