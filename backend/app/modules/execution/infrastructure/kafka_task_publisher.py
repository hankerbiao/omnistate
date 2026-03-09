"""Kafka任务发布器 - Phase 6

Kafka任务发布器负责将outbox事件中的任务数据发布到Kafka队列。
这是发件箱模式的关键组件，确保任务能够可靠地发送到外部测试框架。
现在使用应用级基础设施注册表，不再在构造函数中创建网络连接。
"""

from typing import Dict, Any, Optional
from app.shared.kafka import TaskMessage
from app.shared.core.logger import log as logger
from app.shared.infrastructure import get_kafka_manager


class KafkaTaskPublisher:
    """Kafka任务发布器 - Phase 6

    负责将execution task事件发布到Kafka队列，支持错误处理和重试机制。
    现在使用全局基础设施注册表，在构造函数中不创建任何网络连接。
    """

    def __init__(self):
        """初始化Kafka任务发布器 - 无副作用

        注意：此构造函数现在是无副作用的，不会创建任何网络连接。
        实际的KafkaManager从应用级基础设施注册表中获取。
        """
        # 不再在构造函数中创建KafkaManager
        # 这是一个关键的Phase 6改进
        pass

    async def publish_execution_task(self, event_payload: Dict[str, Any]) -> bool:
        """发布执行任务到Kafka

        Args:
            event_payload: outbox事件负载数据，应包含：
                - task_id: 任务ID
                - external_task_id: 外部任务ID
                - kafka_task_data: Kafka任务数据
                - created_by: 创建者ID

        Returns:
            是否成功发布
        """
        # 从全局基础设施注册表获取KafkaManager
        kafka_manager = get_kafka_manager()
        if not kafka_manager:
            logger.error("Kafka manager not available (infrastructure not initialized)")
            return False

        try:
            # 提取任务数据
            task_id = event_payload.get("task_id")
            external_task_id = event_payload.get("external_task_id")
            kafka_task_data = event_payload.get("kafka_task_data", {})
            created_by = event_payload.get("created_by")

            # 类型检查和验证
            if not task_id or not external_task_id or not kafka_task_data or not created_by:
                logger.error(f"Missing required fields in event payload: {event_payload}")
                return False

            if not isinstance(task_id, str) or not isinstance(external_task_id, str):
                logger.error(f"Invalid field types - task_id and external_task_id must be strings")
                return False

            # 构建Kafka消息
            task_message = TaskMessage(
                task_id=task_id,
                task_type="execution_task",
                task_data=kafka_task_data,
                source="dmlv4-outbox-publisher",
                priority=1
            )

            # 发送任务到Kafka
            success = kafka_manager.send_task(task_message)

            if success:
                logger.info(f"Successfully published task {task_id} to Kafka")
                return True
            else:
                logger.error(f"Failed to publish task {task_id} to Kafka")
                return False

        except Exception as e:
            logger.exception(f"Error publishing task to Kafka: {str(e)}")
            return False

    def is_kafka_available(self) -> bool:
        """检查Kafka是否可用

        Returns:
            Kafka是否可用
        """
        try:
            kafka_manager = get_kafka_manager()
            if not kafka_manager:
                return False
            return kafka_manager.is_available()
        except Exception as e:
            logger.warning(f"Kafka availability check failed: {str(e)}")
            return False

    async def get_kafka_health(self) -> Dict[str, Any]:
        """获取Kafka管理器健康状态

        Returns:
            Kafka健康状态信息
        """
        kafka_manager = get_kafka_manager()
        if not kafka_manager:
            return {
                "status": "NOT_INITIALIZED",
                "message": "Kafka manager not available"
            }

        return kafka_manager.health_check()