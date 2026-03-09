"""发件箱工作器 - Phase 6

发件箱工作器是后台进程，负责读取outbox事件并发布到外部系统（如Kafka）。
这是实现可靠事件发布的关键组件，支持批量处理、重试机制和错误处理。

Phase 6改进：现在使用应用级基础设施注册表，不在构造函数中创建网络连接。

工作流程：
1. 定期查询待处理的outbox事件
2. 批量处理事件并发布到外部系统
3. 更新事件状态（成功/失败）
4. 支持重试机制和错误恢复
5. 记录处理统计和监控信息
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.shared.core.logger import log as logger
from app.shared.integration.outbox_service import OutboxService
from app.shared.infrastructure import get_kafka_manager


class OutboxWorker:
    """发件箱工作器 - Phase 6

    后台工作器，负责读取outbox事件并发布到外部系统。
    支持批量处理、重试机制和错误处理。
    现在使用应用级基础设施注册表，无副作用构造。
    """

    def __init__(
        self,
        batch_size: int = 50,
        poll_interval: int = 5,  # 秒
        max_retries: int = 3
    ):
        """初始化发件箱工作器 - 无副作用

        Args:
            batch_size: 批处理大小
            poll_interval: 轮询间隔（秒）
            max_retries: 最大重试次数

        注意：Phase 6改进 - 此构造函数现在是无副作用的，
        不会创建任何网络连接或后台任务。
        """
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.max_retries = max_retries

        # Phase 6: 延迟初始化服务，不在构造函数中创建
        self._outbox_service: OutboxService | None = None
        self._kafka_manager = None
        self._publisher: Any = None

        self._running = False
        self._task = None

        # 统计信息
        self.stats = {
            "events_processed": 0,
            "events_succeeded": 0,
            "events_failed": 0,
            "last_processed_at": None
        }

    def _get_outbox_service(self) -> OutboxService:
        """获取OutboxService实例（延迟初始化）"""
        if self._outbox_service is None:
            self._outbox_service = OutboxService()
        return self._outbox_service

    def _get_kafka_manager(self):
        """从全局基础设施注册表获取Kafka管理器"""
        if self._kafka_manager is None:
            self._kafka_manager = get_kafka_manager()
        return self._kafka_manager

    @property
    def publisher(self) -> Any:
        """获取Kafka任务发布器实例（延迟初始化）"""
        if self._publisher is None:
            from app.modules.execution.infrastructure.kafka_task_publisher import KafkaTaskPublisher
            self._publisher = KafkaTaskPublisher()
        return self._publisher

    @property
    def outbox_service(self) -> OutboxService:
        """获取OutboxService实例（延迟初始化）"""
        return self._get_outbox_service()

    async def start(self) -> None:
        """启动发件箱工作器"""
        if self._running:
            logger.warning("Outbox worker is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_worker())
        logger.info("Outbox worker started")

    async def stop(self) -> None:
        """停止发件箱工作器"""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Outbox worker stopped")

    async def _run_worker(self) -> None:
        """工作器主循环"""
        logger.info("Outbox worker main loop started")

        try:
            while self._running:
                try:
                    await self._process_batch()
                    await asyncio.sleep(self.poll_interval)
                except Exception as e:
                    logger.exception(f"Error in outbox worker main loop: {str(e)}")
                    await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            logger.info("Outbox worker main loop cancelled")
        except Exception as e:
            logger.exception(f"Unexpected error in outbox worker: {str(e)}")
        finally:
            logger.info("Outbox worker main loop ended")

    async def _process_batch(self) -> None:
        """批量处理outbox事件"""
        # 获取待处理的事件
        events = await self._get_outbox_service().get_pending_events(self.batch_size)

        if not events:
            return

        logger.info(f"Processing batch of {len(events)} outbox events")

        # 按事件类型分组处理
        events_by_type = self._group_events_by_type(events)

        for event_type, type_events in events_by_type.items():
            await self._process_events_of_type(event_type, type_events)

        # 更新统计信息
        self.stats["events_processed"] += len(events)
        self.stats["last_processed_at"] = datetime.now(timezone.utc)

    def _group_events_by_type(self, events: List) -> Dict[str, List]:
        """按事件类型分组事件"""
        events_by_type = {}
        for event in events:
            event_type = event.event_type
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
        return events_by_type

    async def _process_events_of_type(self, event_type: str, events: List) -> None:
        """处理指定类型的事件

        Args:
            event_type: 事件类型
            events: 事件列表
        """
        if event_type == "execution_task_dispatched":
            await self._process_execution_task_events(events)
        else:
            logger.warning(f"Unknown event type: {event_type}, skipping {len(events)} events")

    async def _process_execution_task_events(self, events: List) -> None:
        """处理执行任务分发事件

        Args:
            events: execution_task_dispatched事件列表
        """
        for event in events:
            try:
                success = await self._publish_execution_task_event(event)
                outbox_service = self._get_outbox_service()
                if success:
                    await outbox_service.mark_event_as_sent(event.event_id)
                    self.stats["events_succeeded"] += 1
                    logger.debug(f"Successfully processed event: {event.event_id}")
                else:
                    await self._handle_publish_failure(event, outbox_service)
                    self.stats["events_failed"] += 1

            except Exception as e:
                logger.exception(f"Error processing event {event.event_id}: {str(e)}")
                outbox_service = self._get_outbox_service()
                await outbox_service.mark_event_as_failed(
                    event.event_id,
                    f"Processing error: {str(e)}"
                )
                self.stats["events_failed"] += 1

    async def _publish_execution_task_event(self, event) -> bool:
        """发布执行任务事件到Kafka

        Args:
            event: outbox事件

        Returns:
            是否成功发布
        """
        try:
            # 检查Kafka是否可用
            if not self.publisher.is_kafka_available():
                logger.warning("Kafka is not available, will retry later")
                return False

            # 发布任务
            return await self.publisher.publish_execution_task(event.payload)

        except Exception as e:
            logger.exception(f"Error publishing execution task: {str(e)}")
            return False

    async def _handle_publish_failure(self, event, outbox_service: OutboxService) -> None:
        """处理发布失败

        Args:
            event: 失败的outbox事件
            outbox_service: OutboxService实例
        """
        error_message = "Failed to publish to Kafka"

        # 检查是否达到最大重试次数
        if event.retry_count >= self.max_retries:
            await outbox_service.mark_event_as_failed(
                event.event_id,
                f"{error_message}: max retries exceeded"
            )
            logger.error(f"Permanently failed event {event.event_id}: max retries exceeded")
        else:
            await outbox_service.mark_event_as_failed(event.event_id, error_message)
            logger.warning(f"Failed event {event.event_id} will be retried (attempt {event.retry_count + 1})")

    def get_stats(self) -> Dict[str, Any]:
        """获取工作器统计信息

        Returns:
            统计信息字典
        """
        return {
            "running": self._running,
            "batch_size": self.batch_size,
            "poll_interval": self.poll_interval,
            "max_retries": self.max_retries,
            "stats": self.stats.copy()
        }

    async def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康状态信息
        """
        # 检查outbox中失败事件的数量
        failed_events_count = await self.outbox_service.get_failed_events_count()

        # 检查Kafka可用性
        kafka_available = self.publisher.is_kafka_available()

        return {
            "worker_running": self._running,
            "kafka_available": kafka_available,
            "failed_events_count": failed_events_count,
            "stats": self.stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# 全局发件箱工作器实例
_outbox_worker: OutboxWorker | None = None


async def get_outbox_worker() -> OutboxWorker:
    """获取全局发件箱工作器实例

    Returns:
        发件箱工作器实例
    """
    global _outbox_worker
    if _outbox_worker is None:
        _outbox_worker = OutboxWorker()
    return _outbox_worker


async def start_outbox_worker() -> None:
    """启动全局发件箱工作器"""
    worker = await get_outbox_worker()
    await worker.start()


async def stop_outbox_worker() -> None:
    """停止全局发件箱工作器"""
    worker = await get_outbox_worker()
    await worker.stop()