"""
Kafka 消息管理类 - 用于任务下发和接收
提供完整的 Kafka 生产者和消费者功能，支持任务分发和结果收集
"""

import json
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime, UTC
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError, KafkaTimeoutError


class TaskMessage:
    """任务消息数据结构"""

    def __init__(self, task_id: str, task_type: str, task_data: Dict[str, Any],
                 source: str = "dmlv4-system", priority: int = 1):
        self.task_id = task_id
        self.task_type = task_type
        self.task_data = task_data
        self.source = source
        self.priority = priority
        self.create_time = datetime.now(UTC).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "task_data": self.task_data,
            "source": self.source,
            "priority": self.priority,
            "create_time": self.create_time
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(',', ':'))

    @classmethod
    def from_json(cls, json_str: str) -> 'TaskMessage':
        """从 JSON 字符串创建实例"""
        data = json.loads(json_str)
        msg = cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            task_data=data["task_data"],
            source=data.get("source", "dmlv4-system"),
            priority=data.get("priority", 1)
        )
        return msg


class ResultMessage:
    """结果消息数据结构"""

    def __init__(self, task_id: str, status: str, result_data: Optional[Dict[str, Any]] = None,
                 error_message: Optional[str] = None, executor: str = "unknown"):
        self.task_id = task_id
        self.status = status  # SUCCESS, FAILED, RUNNING
        self.result_data = result_data or {}
        self.error_message = error_message
        self.executor = executor
        self.complete_time = datetime.now(UTC).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "executor": self.executor,
            "complete_time": self.complete_time
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(',', ':'))

    @classmethod
    def from_json(cls, json_str: str) -> 'ResultMessage':
        """从 JSON 字符串创建实例"""
        data = json.loads(json_str)
        return cls(
            task_id=data["task_id"],
            status=data["status"],
            result_data=data.get("result_data"),
            error_message=data.get("error_message"),
            executor=data.get("executor", "unknown")
        )


class KafkaMessageManager:
    """Kafka 消息管理类 - 任务分发和结果收集的核心组件"""

    def __init__(self, bootstrap_servers: List[str] = None, client_id: str = "dmlv4-shard"):
        """
        初始化 Kafka 消息管理器

        Args:
            bootstrap_servers: Kafka 集群地址列表
            client_id: 客户端 ID
        """
        self.bootstrap_servers = bootstrap_servers or ["10.17.154.252:9092"]
        self.client_id = client_id
        self.logger = logging.getLogger(__name__)

        # 生产者和消费者
        self.producer: Optional[KafkaProducer] = None
        self.consumers: Dict[str, KafkaConsumer] = {}

        # 主题名称
        self.task_topic = "dmlv4.tasks"
        self.result_topic = "dmlv4.results"
        self.dead_letter_topic = "dmlv4.deadletter"

        # 任务处理回调函数
        self.task_handlers: Dict[str, Callable] = {}

        # 状态标记
        self.is_running = False

    def _create_producer(self) -> KafkaProducer:
        """创建 Kafka 生产者"""
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda v: v.encode('utf-8') if isinstance(v, str) else v,
                key_serializer=lambda k: k.encode('utf-8') if isinstance(k, str) else k,
                acks='all',  # 所有副本确认
                retries=3,   # 重试3次
                batch_size=16384,  # 批处理大小
                linger_ms=10,      # 批处理延迟
                buffer_memory=33554432,  # 32MB 缓冲区
            )
            self.logger.info(f"Kafka 生产者创建成功，连接到 {self.bootstrap_servers}")
            return producer
        except Exception as e:
            self.logger.error(f"创建 Kafka 生产者失败: {e}")
            raise

    def _create_consumer(self, group_id: str, topics: List[str]) -> KafkaConsumer:
        """创建 Kafka 消费者"""
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=f"{self.client_id}-{group_id}",
                group_id=group_id,
                value_deserializer=lambda m: m.decode('utf-8') if m else None,
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000,
                max_poll_records=100,
                consumer_timeout_ms=1000
            )
            consumer.subscribe(topics)
            self.logger.info(f"Kafka 消费者创建成功，组ID: {group_id}, 主题: {topics}")
            return consumer
        except Exception as e:
            self.logger.error(f"创建 Kafka 消费者失败: {e}")
            raise

    def start(self):
        """启动消息管理器"""
        try:
            self.producer = self._create_producer()

            # 创建任务消费者
            task_consumer = self._create_consumer(
                group_id="dmlv4-task-handlers",
                topics=[self.task_topic]
            )
            self.consumers['task'] = task_consumer

            # 创建结果消费者
            result_consumer = self._create_consumer(
                group_id="dmlv4-result-collectors",
                topics=[self.result_topic]
            )
            self.consumers['result'] = result_consumer

            # 创建死信队列消费者
            dlq_consumer = self._create_consumer(
                group_id="dmlv4-dlq-handlers",
                topics=[self.dead_letter_topic]
            )
            self.consumers['deadletter'] = dlq_consumer

            self.is_running = True
            self.logger.info("Kafka 消息管理器启动成功")

        except Exception as e:
            self.logger.error(f"启动 Kafka 消息管理器失败: {e}")
            raise

    def stop(self):
        """停止消息管理器"""
        try:
            # 关闭所有消费者
            for name, consumer in self.consumers.items():
                if consumer:
                    consumer.close()
                    self.logger.info(f"关闭 {name} 消费者")

            # 关闭生产者
            if self.producer:
                self.producer.close()
                self.logger.info("关闭生产者")

            self.is_running = False
            self.logger.info("Kafka 消息管理器已停止")

        except Exception as e:
            self.logger.error(f"停止 Kafka 消息管理器时出错: {e}")

    def send_task(self, task_message: TaskMessage, priority: int = 0) -> bool:
        """
        发送任务消息

        Args:
            task_message: 任务消息对象
            priority: 消息优先级（0=正常, 1=高优先级, 2=紧急）

        Returns:
            bool: 发送是否成功
        """
        if not self.is_running or not self.producer:
            self.logger.error("消息管理器未启动或生产者不可用")
            return False

        try:
            # 使用任务 ID 作为消息键，保证相同任务发送到同一分区
            key = task_message.task_id
            value = task_message.to_json()

            # 根据优先级设置消息头
            headers = [
                ('priority', str(priority).encode('utf-8')),
                ('task_type', task_message.task_type.encode('utf-8')),
                ('source', task_message.source.encode('utf-8'))
            ]

            # 发送消息
            future = self.producer.send(
                topic=self.task_topic,
                key=key,
                value=value,
                headers=headers
            )

            # 同步等待发送结果
            record_metadata = future.get(timeout=10)

            self.logger.info(
                f"任务发送成功 - ID: {task_message.task_id}, "
                f"主题: {record_metadata.topic}, "
                f"分区: {record_metadata.partition}, "
                f"偏移量: {record_metadata.offset}"
            )
            return True

        except KafkaTimeoutError:
            self.logger.error(f"任务发送超时 - ID: {task_message.task_id}")
            return False
        except KafkaError as e:
            self.logger.error(f"发送任务时发生 Kafka 错误 - ID: {task_message.task_id}, 错误: {e}")
            return False
        except Exception as e:
            self.logger.error(f"发送任务时发生未知错误 - ID: {task_message.task_id}, 错误: {e}")
            return False

    def send_result(self, result_message: ResultMessage) -> bool:
        """
        发送结果消息

        Args:
            result_message: 结果消息对象

        Returns:
            bool: 发送是否成功
        """
        if not self.is_running or not self.producer:
            self.logger.error("消息管理器未启动或生产者不可用")
            return False

        try:
            key = result_message.task_id
            value = result_message.to_json()

            headers = [
                ('status', result_message.status.encode('utf-8')),
                ('executor', result_message.executor.encode('utf-8'))
            ]

            future = self.producer.send(
                topic=self.result_topic,
                key=key,
                value=value,
                headers=headers
            )

            record_metadata = future.get(timeout=10)

            self.logger.info(
                f"结果发送成功 - 任务ID: {result_message.task_id}, "
                f"状态: {result_message.status}"
            )
            return True

        except Exception as e:
            self.logger.error(f"发送结果时发生错误 - 任务ID: {result_message.task_id}, 错误: {e}")
            return False

    def send_to_dead_letter_queue(self, original_message: Union[TaskMessage, str],
                                  error_reason: str) -> bool:
        """
        发送消息到死信队列

        Args:
            original_message: 原始消息或消息字符串
            error_reason: 错误原因

        Returns:
            bool: 发送是否成功
        """
        if not self.is_running or not self.producer:
            return False

        try:
            if isinstance(original_message, TaskMessage):
                value = original_message.to_json()
                key = original_message.task_id
            else:
                value = original_message
                key = "unknown"

            dlq_data = {
                "original_message": value,
                "error_reason": error_reason,
                "dead_letter_time": datetime.utcnow().isoformat(),
                "original_key": key
            }

            dlq_value = json.dumps(dlq_data, ensure_ascii=False, separators=(',', ':'))

            future = self.producer.send(
                topic=self.dead_letter_topic,
                key=key,
                value=dlq_value
            )

            record_metadata = future.get(timeout=10)
            self.logger.warning(f"消息已发送到死信队列 - Key: {key}, 原因: {error_reason}")
            return True

        except Exception as e:
            self.logger.error(f"发送死信消息时发生错误: {e}")
            return False

    def register_task_handler(self, task_type: str, handler_func: Callable):
        """
        注册任务处理器，注册表模式

        Args:
            task_type: 任务类型
            handler_func: 处理函数，应该接收 TaskMessage 并返回 ResultMessage
        """
        self.task_handlers[task_type] = handler_func
        self.logger.info(f"已注册任务处理器 - 类型: {task_type}")

    def process_tasks(self, max_tasks: int = None):
        """
        处理任务消息（同步模式）

        Args:
            max_tasks: 最大处理任务数，None 表示无限
        """
        if 'task' not in self.consumers:
            self.logger.error("任务消费者未初始化")
            return

        consumer = self.consumers['task']
        processed_count = 0

        try:
            self.logger.info("开始处理任务消息...")

            while self.is_running:
                # 检查是否达到最大处理数量
                if max_tasks and processed_count >= max_tasks:
                    self.logger.info(f"已达到最大处理任务数: {max_tasks}")
                    break

                # 拉取消息
                msg_pack = consumer.poll(timeout_ms=1000)

                if not msg_pack:
                    continue

                for topic_partition, messages in msg_pack.items():
                    for message in messages:
                        try:
                            # 解析任务消息
                            task_msg = TaskMessage.from_json(message.value)

                            self.logger.info(f"处理任务 - ID: {task_msg.task_id}, 类型: {task_msg.task_type}")

                            # 查找对应的处理器
                            handler = self.task_handlers.get(task_msg.task_type)
                            if not handler:
                                error_msg = f"未找到任务类型 {task_msg.task_type} 的处理器"
                                self.logger.error(error_msg)
                                self.send_to_dead_letter_queue(task_msg, error_msg)
                                continue

                            # 执行任务处理
                            try:
                                result = handler(task_msg)

                                # 发送结果
                                if isinstance(result, ResultMessage):
                                    self.send_result(result)
                                else:
                                    # 假设处理器返回布尔值表示成功/失败
                                    status = "SUCCESS" if result else "FAILED"
                                    result_msg = ResultMessage(
                                        task_id=task_msg.task_id,
                                        status=status
                                    )
                                    self.send_result(result_msg)

                                processed_count += 1

                            except Exception as e:
                                self.logger.error(f"处理任务时发生错误 - ID: {task_msg.task_id}, 错误: {e}")
                                error_result = ResultMessage(
                                    task_id=task_msg.task_id,
                                    status="FAILED",
                                    error_message=str(e)
                                )
                                self.send_result(error_result)

                        except Exception as e:
                            self.logger.error(f"解析任务消息时发生错误: {e}")
                            self.send_to_dead_letter_queue(message.value, f"消息解析错误: {e}")

        except Exception as e:
            self.logger.error(f"处理任务时发生严重错误: {e}")

    async def process_tasks_async(self, max_tasks: int = None):
        """异步处理任务消息"""
        # 简化的异步处理 - 在实际项目中可以使用 aiokafka
        # 这里先提供基础框架
        self.logger.info("异步任务处理模式启动")
        self.process_tasks(max_tasks)

    def collect_results(self, timeout_ms: int = 5000) -> List[ResultMessage]:
        """
        收集结果消息

        Args:
            timeout_ms: 消费者超时时间

        Returns:
            List[ResultMessage]: 结果消息列表
        """
        if 'result' not in self.consumers:
            self.logger.error("结果消费者未初始化")
            return []

        consumer = self.consumers['result']
        results = []

        try:
            msg_pack = consumer.poll(timeout_ms=timeout_ms)

            for topic_partition, messages in msg_pack.items():
                for message in messages:
                    try:
                        result_msg = ResultMessage.from_json(message.value)
                        results.append(result_msg)
                        self.logger.info(f"收集到结果 - 任务ID: {result_msg.task_id}, 状态: {result_msg.status}")

                    except Exception as e:
                        self.logger.error(f"解析结果消息时发生错误: {e}")

        except Exception as e:
            self.logger.error(f"收集结果时发生错误: {e}")

        return results

    def get_consumer_lag(self) -> Dict[str, Dict[str, int]]:
        """获取消费者滞后信息"""
        lag_info = {}

        for name, consumer in self.consumers.items():
            try:
                # 获取消费者组信息
                partitions = consumer.assignment()
                lag_info[name] = {}

                for tp in partitions:
                    # 这里简化处理，实际应该调用 AdminClient 获取滞后信息
                    lag_info[name][tp.topic] = lag_info[name].get(tp.topic, 0) + 0

            except Exception as e:
                self.logger.error(f"获取 {name} 消费者滞后信息时出错: {e}")
                lag_info[name] = {"error": str(e)}

        return lag_info

    def is_available(self) -> bool:
        """检查Kafka消息管理器是否可用

        Returns:
            Kafka管理器是否可用
        """
        return self.is_running and self.producer is not None

    def health_check(self) -> Dict[str, Any]:
        """执行Kafka消息管理器的健康检查

        Returns:
            健康检查结果字典
        """
        health_status = {
            "component": "kafka_message_manager",
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "UNKNOWN"
        }

        try:
            if not self.is_running:
                health_status["status"] = "STOPPED"
                health_status["message"] = "Kafka message manager is not running"
                return health_status

            if not self.producer:
                health_status["status"] = "DEGRADED"
                health_status["message"] = "Kafka producer is not available"
                return health_status

            # 检查生产者是否响应（简化检查）
            if hasattr(self.producer, '_closed') and self.producer._closed:
                health_status["status"] = "DEGRADED"
                health_status["message"] = "Kafka producer appears to be closed"
                return health_status

            health_status["status"] = "HEALTHY"
            health_status["message"] = "Kafka message manager is operating normally"
            health_status["details"] = {
                "is_running": self.is_running,
                "bootstrap_servers": self.bootstrap_servers,
                "client_id": self.client_id,
                "producer_available": self.producer is not None,
                "consumer_count": len(self.consumers),
                "topics": {
                    "task_topic": self.task_topic,
                    "result_topic": self.result_topic,
                    "dead_letter_topic": self.dead_letter_topic
                }
            }

        except Exception as e:
            health_status["status"] = "ERROR"
            health_status["message"] = f"Health check failed: {str(e)}"
            self.logger.exception(f"Kafka health check error: {str(e)}")

        return health_status

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()


    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()