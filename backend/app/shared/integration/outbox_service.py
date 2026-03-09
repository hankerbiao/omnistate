"""发件箱服务

发件箱服务负责管理outbox事件的生命周期，包括创建、更新和查询outbox事件。
这是实现可靠事件发布的核心组件，支持重试机制和错误处理。
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pymongo import AsyncMongoClient
from pymongo.asynchronous.client_session import AsyncClientSession

from app.shared.core.logger import log as logger
from app.shared.core.mongo_client import get_mongo_client
from app.shared.integration.outbox_models import OutboxEventDoc


class OutboxService:
    """发件箱服务类

    负责outbox事件的创建、查询和状态管理，支持可靠的事件发布。
    """

    def __init__(self):
        """初始化发件箱服务"""
        self._mongo_client = self._get_mongo_client_or_none()

    async def create_execution_task_event(
        self,
        task_id: str,
        external_task_id: str,
        kafka_task_data: Dict[str, Any],
        created_by: str,
        session: Optional[AsyncClientSession] = None
    ) -> OutboxEventDoc:
        """创建执行任务分发事件

        Args:
            task_id: 任务ID
            external_task_id: 外部任务ID
            kafka_task_data: Kafka任务数据
            created_by: 创建者ID
            session: 可选的MongoDB会话（用于事务）

        Returns:
            创建的outbox事件文档
        """
        event_doc = OutboxEventDoc(
            event_id=str(uuid.uuid4()),
            aggregate_type="ExecutionTask",
            aggregate_id=task_id,
            event_type="execution_task_dispatched",
            payload={
                "task_id": task_id,
                "external_task_id": external_task_id,
                "kafka_task_data": kafka_task_data,
                "created_by": created_by,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        await event_doc.insert(session=session)
        logger.info(f"Created outbox event for task {task_id}: {event_doc.event_id}")
        return event_doc

    async def get_pending_events(self, limit: int = 100) -> List[OutboxEventDoc]:
        """获取待处理的事件

        获取所有状态为PENDING或FAILED且可以重试的事件，按创建时间排序。
        用于后台工作器批量处理outbox事件。

        Args:
            limit: 返回事件数量限制

        Returns:
            待处理的outbox事件列表
        """
        current_time = datetime.now(timezone.utc)

        # 查询条件：状态为PENDING，或状态为FAILED且可以重试
        query = {
            "$or": [
                {"status": "PENDING"},
                {
                    "$and": [
                        {"status": "FAILED"},
                        {"next_retry_at": {"$lte": current_time}}
                    ]
                }
            ]
        }

        events = await OutboxEventDoc.find(query).sort("created_at").limit(limit).to_list()
        logger.info(f"Found {len(events)} pending outbox events")
        return events

    async def mark_event_as_sent(self, event_id: str) -> bool:
        """标记事件为已发送

        Args:
            event_id: 事件ID

        Returns:
            是否成功更新
        """
        event = await OutboxEventDoc.find_one({"event_id": event_id})
        if not event:
            logger.warning(f"Outbox event not found: {event_id}")
            return False

        event.mark_as_sent()
        await event.save()
        logger.info(f"Marked outbox event as sent: {event_id}")
        return True

    async def mark_event_as_failed(self, event_id: str, error_message: str) -> bool:
        """标记事件为失败

        Args:
            event_id: 事件ID
            error_message: 错误信息

        Returns:
            是否成功更新
        """
        event = await OutboxEventDoc.find_one({"event_id": event_id})
        if not event:
            logger.warning(f"Outbox event not found: {event_id}")
            return False

        event.mark_as_failed(error_message)
        await event.save()

        if event.status == "PERMANENTLY_FAILED":
            logger.error(f"Outbox event permanently failed: {event_id}, error: {error_message}")
        else:
            logger.warning(f"Outbox event failed (retry {event.retry_count}): {event_id}, error: {error_message}")

        return True

    async def get_failed_events_count(self) -> int:
        """获取失败事件数量

        Returns:
            失败事件总数
        """
        count = await OutboxEventDoc.find({"status": {"$in": ["FAILED", "PERMANENTLY_FAILED"]}}).count()
        return count

    async def get_events_by_aggregate(self, aggregate_type: str, aggregate_id: str) -> List[OutboxEventDoc]:
        """根据聚合信息获取事件

        Args:
            aggregate_type: 聚合类型
            aggregate_id: 聚合ID

        Returns:
            匹配的事件列表
        """
        events = await OutboxEventDoc.find({
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id
        }).sort("created_at").to_list()
        return events

    async def cleanup_old_events(self, days: int = 7) -> int:
        """清理旧事件

        清理已成功发送且超过指定天数的outbox事件。

        Args:
            days: 保留天数

        Returns:
            清理的事件数量
        """
        cutoff_date = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)
        result = await OutboxEventDoc.find({
            "status": "SENT",
            "sent_at": {"$lte": cutoff_date}
        }).delete()

        deleted_count = result.deleted_count if hasattr(result, 'deleted_count') else 0
        logger.info(f"Cleaned up {deleted_count} old outbox events")
        return deleted_count

    @staticmethod
    def _get_mongo_client_or_none() -> Optional[AsyncMongoClient]:
        """获取全局 Mongo 客户端

        返回 None 表示当前运行上下文未初始化客户端（例如某些测试环境）。
        """
        try:
            return get_mongo_client()
        except RuntimeError:
            return None