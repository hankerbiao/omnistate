from kafka import KafkaProducer, KafkaConsumer


class KafkaTaskHandler:
    """
    用于处理向Kafka发送任务和从Kafka接收结果的类。
    该类使用kafka-python库与Kafka代理进行交互。

    假设条件：
    - Kafka代理运行在'localhost:9092'。可在__init__中修改此设置。
    - 消息以UTF-8编码的字符串格式发送和接收。如需其他格式（如JSON）请自行调整。
    - 消费者方法运行在循环中持续接收消息。如需单次消息消费可根据需求进行修改。
    """

    def __init__(self, bootstrap_servers='localhost:9092'):
        """
        初始化Kafka生产者与消费者。

        :param bootstrap_servers: Kafka代理服务器列表（默认：'localhost:9092'）
        """
        # 初始化生产者
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: v.encode('utf-8') if isinstance(v, str) else v
        )

        # 初始化消费者
        self.consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: m.decode('utf-8'),
            auto_offset_reset='earliest',  # 如果没有偏移量则从头开始
            enable_auto_commit=True,  # 自动提交偏移量
            group_id='task-handler-group'  # 消费者组ID
        )

    def send_task(self, topic, task_data):
        """
        向指定的Kafka主题发送任务。

        :param topic: 发送任务的Kafka主题名称
        :param task_data: 要发送的任务数据（字符串或字节）
        """
        # 发送消息到主题
        future = self.producer.send(topic, value=task_data)

        # 阻塞直到消息发送完成（可选，用于同步发送）
        try:
            record_metadata = future.get(timeout=10)
            print(f"任务已发送到主题'{topic}'，分区：{record_metadata.partition}，偏移量：{record_metadata.offset}")
        except Exception as e:
            print(f"发送任务时出错：{e}")

        # 刷新确保所有消息都被发送
        self.producer.flush()

    def receive_result(self, topic, timeout_ms=1000):
        """
        从指定的Kafka主题接收结果。
        该方法订阅主题并在循环中轮询消息。
        对接收到的每个消息进行yield处理。

        :param topic: 接收结果的Kafka主题名称
        :param timeout_ms: 轮询超时时间（毫秒，默认1000）
        :yield: 解码后的消息值（字符串）

        注意：这是一个无限运行的生成器。生产环境中可能需要添加停止条件。
        """
        # 订阅主题
        self.consumer.subscribe([topic])

        print(f"已订阅主题'{topic}'。等待消息中...")

        while True:
            # 轮询消息
            messages = self.consumer.poll(timeout_ms=timeout_ms)

            for tp, msg_list in messages.items():
                for msg in msg_list:
                    yield msg.value  # yield解码后的消息
                    print(f"从主题'{topic}'接收到结果：{msg.value}")

# 使用示例（已注释；取消注释以测试）
# if __name__ == "__main__":
#     handler = KafkaTaskHandler()
#
#     # 发送任务
#     handler.send_task('task-topic', '这是一个示例任务')
#
#     # 接收结果（将循环执行）
#     for result in handler.receive_result('result-topic'):
#         print(f"处理结果：{result}")
#         # 如需要可添加跳出循环的逻辑