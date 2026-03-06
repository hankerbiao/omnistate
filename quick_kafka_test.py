#!/usr/bin/env python3
"""
快速 Kafka 连通性测试

直接测试 Kafka 连接，不依赖后端 API。
用于验证 Kafka 服务是否正常运行。

使用方法:
    python quick_kafka_test.py
"""

import json
import logging
import os
import time
from datetime import datetime

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "10.17.154.252:9092").split(",")
TEST_TOPIC = "dmlv4.tasks"


def test_producer():
    """测试 Kafka 生产者"""
    logger.info("=" * 80)
    logger.info("测试 Kafka 生产者")
    logger.info("=" * 80)

    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_SERVERS,
            client_id=f"test-producer-{int(time.time())}",
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks=1,  # 简化配置
            retries=3,
        )

        # 发送测试消息
        test_message = {
            "task_id": f"TEST-{int(time.time())}",
            "task_type": "test_message",
            "task_data": {
                "test": True,
                "timestamp": datetime.now().isoformat(),
                "message": "这是一条测试消息"
            },
            "source": "kafka-test-script",
            "priority": 1,
            "create_time": datetime.now().isoformat()
        }

        future = producer.send(
            topic=TEST_TOPIC,
            key=test_message["task_id"],
            value=test_message
        )

        # 等待发送确认
        record_metadata = future.get(timeout=10)

        producer.close()

        logger.info("✓ 消息发送成功")
        logger.info(f"  主题: {record_metadata.topic}")
        logger.info(f"  分区: {record_metadata.partition}")
        logger.info(f"  偏移: {record_metadata.offset}")
        logger.info(f"  消息内容: {json.dumps(test_message, ensure_ascii=False, indent=2)}")

        return True

    except KafkaError as e:
        logger.error(f"✗ Kafka 错误: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ 发生错误: {e}")
        return False


def test_consumer():
    """测试 Kafka 消费者"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 Kafka 消费者")
    logger.info("=" * 80)

    try:
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_SERVERS,
            client_id=f"test-consumer-{int(time.time())}",
            group_id=f"test-group-{int(time.time())}",
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            session_timeout_ms=10000,
            consumer_timeout_ms=2000
        )

        # 订阅主题
        consumer.subscribe([TEST_TOPIC])

        logger.info(f"正在监听主题: {TEST_TOPIC}")
        logger.info("等待 5 秒接收消息...")

        # 等待消息
        start_time = time.time()
        timeout = 5
        messages_received = 0

        while time.time() - start_time < timeout:
            msg_pack = consumer.poll(timeout_ms=1000)

            for topic_partition, messages in msg_pack.items():
                for msg in messages:
                    messages_received += 1
                    logger.info(f"\n✓ 收到消息 #{messages_received}")
                    logger.info(f"  主题: {msg.topic}")
                    logger.info(f"  分区: {msg.partition}")
                    logger.info(f"  偏移: {msg.offset}")
                    logger.info(f"  键: {msg.key}")
                    logger.info(f"  值: {json.dumps(msg.value, ensure_ascii=False, indent=2)}")

        consumer.close()

        if messages_received > 0:
            logger.info(f"\n✓ 测试成功，共收到 {messages_received} 条消息")
            return True
        else:
            logger.warning(f"\n⚠ 未在 {timeout} 秒内收到消息")
            logger.warning("  可能原因:")
            logger.warning("  1. 没有生产者发送消息")
            logger.warning("  2. 消费者组偏移量问题")
            logger.warning("  3. 主题不存在或没有权限")
            return False

    except Exception as e:
        logger.error(f"✗ 消费者测试失败: {e}")
        return False


def main():
    """主测试流程"""
    logger.info("=" * 80)
    logger.info("DMLv4 Kafka 快速连通性测试")
    logger.info("=" * 80)
    logger.info(f"Kafka 服务器: {KAFKA_SERVERS}")
    logger.info(f"测试主题: {TEST_TOPIC}")
    logger.info("=" * 80)

    # 测试生产者
    producer_ok = test_producer()

    # 测试消费者
    consumer_ok = test_consumer()

    # 输出结果
    logger.info("\n" + "=" * 80)
    logger.info("测试结果汇总")
    logger.info("=" * 80)
    logger.info(f"Kafka 生产者: {'✓ 正常' if producer_ok else '✗ 失败'}")
    logger.info(f"Kafka 消费者: {'✓ 正常' if consumer_ok else '✗ 失败'}")
    logger.info("=" * 80)

    if producer_ok and consumer_ok:
        logger.info("\n🎉 Kafka 连接测试通过！")
        logger.info("可以运行完整集成测试: python test_kafka_integration.py")
    else:
        logger.error("\n❌ Kafka 连接测试失败")
        logger.error("请检查:")
        logger.error("  1. Kafka 服务是否运行")
        logger.error("  2. Kafka 地址和端口是否正确")
        logger.error("  3. 网络连通性")
        logger.error("  4. Kafka 主题是否存在")


if __name__ == "__main__":
    main()