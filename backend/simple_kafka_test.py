#!/usr/bin/env python3
"""
简单的 Kafka 消息发送测试

这个脚本直接测试：
1. 向 dmlv4.tasks 主题发送测试消息
2. 验证消息是否成功发送
3. 可选：监听并验证消息是否被接收

使用方法:
    python simple_kafka_test.py
"""

import json
import logging
import os
import sys
import time
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径到 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    # 导入 Kafka 消息管理器
    from app.shared.kafka.kafka_message_manager import KafkaMessageManager, TaskMessage
    logger.info("✓ 成功导入 KafkaMessageManager")
except ImportError as e:
    logger.error(f"✗ 导入失败: {e}")
    logger.error("请确保在项目根目录运行此脚本")
    sys.exit(1)


def test_kafka_producer():
    """测试 Kafka 生产者 - 发送消息"""
    logger.info("=" * 80)
    logger.info("测试 Kafka 生产者 - 发送消息")
    logger.info("=" * 80)

    try:
        # 创建消息管理器
        mgr = KafkaMessageManager(
            bootstrap_servers=["10.17.154.252:9092"],
            client_id="test-producer"
        )

        # 启动管理器
        logger.info("启动 Kafka 消息管理器...")
        mgr.start()
        logger.info("✓ 消息管理器启动成功")

        # 创建测试任务消息
        test_message = TaskMessage(
            task_id=f"TEST-{int(time.time())}",
            task_type="test_execution",
            task_data={
                "test_name": "DDR5 Memory Test",
                "duration": 5,
                "framework": "pytest",
                "dut": {
                    "hostname": "test-server-01",
                    "memory": "32GB"
                }
            },
            source="simple-test-script",
            priority=1
        )

        logger.info(f"创建测试消息:")
        logger.info(f"  任务ID: {test_message.task_id}")
        logger.info(f"  任务类型: {test_message.task_type}")
        logger.info(f"  来源: {test_message.source}")

        # 发送消息
        logger.info("\n发送消息到 Kafka...")
        success = mgr.send_task(test_message)

        if success:
            logger.info("✓✓✓ 消息发送成功！")
            logger.info(f"  主题: dmlv4.tasks")
            logger.info(f"  消息内容: {json.dumps(test_message.to_dict(), ensure_ascii=False, indent=2)}")
            return test_message.task_id, True
        else:
            logger.error("✗✗✗ 消息发送失败！")
            return None, False

    except Exception as e:
        logger.error(f"✗✗✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None, False
    finally:
        try:
            mgr.stop()
            logger.info("✓ 消息管理器已停止")
        except:
            pass


def test_kafka_consumer():
    """测试 Kafka 消费者 - 接收消息"""
    logger.info("\n" + "=" * 80)
    logger.info("测试 Kafka 消费者 - 接收消息")
    logger.info("=" * 80)

    try:
        # 创建简单的消费者
        from kafka import KafkaConsumer

        consumer = KafkaConsumer(
            bootstrap_servers=["10.17.154.252:9092"],
            client_id=f"test-consumer-{int(time.time())}",
            group_id=f"test-group-{int(time.time())}",
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            session_timeout_ms=10000,
            consumer_timeout_ms=5000
        )

        # 订阅主题
        consumer.subscribe(['dmlv4.tasks'])
        logger.info("✓ 消费者已启动，订阅主题: dmlv4.tasks")
        logger.info("等待 10 秒接收消息...\n")

        # 等待消息
        start_time = time.time()
        messages = []

        while time.time() - start_time < 10:
            msg_pack = consumer.poll(timeout_ms=1000)

            if msg_pack:
                for topic_partition, msg_list in msg_pack.items():
                    for msg in msg_list:
                        messages.append(msg)
                        logger.info(f"✓ 收到消息:")
                        logger.info(f"  主题: {msg.topic}")
                        logger.info(f"  分区: {msg.partition}")
                        logger.info(f"  偏移: {msg.offset}")
                        logger.info(f"  任务ID: {msg.key}")
                        if msg.value:
                            logger.info(f"  任务类型: {msg.value.get('task_type')}")
                            logger.info(f"  来源: {msg.value.get('source')}")
                        logger.info("")

        consumer.close()

        if messages:
            logger.info(f"✓✓✓ 成功接收 {len(messages)} 条消息")
            return True
        else:
            logger.warning("⚠ 未接收到任何消息")
            logger.warning("  这可能是因为:")
            logger.warning("  1. 没有生产者发送消息")
            logger.warning("  2. 消费者组偏移量问题")
            return False

    except Exception as e:
        logger.error(f"✗✗✗ 消费者测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    logger.info("=" * 80)
    logger.info("DMLv4 简单 Kafka 测试")
    logger.info("=" * 80)
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Kafka 服务器: 10.17.154.252:9092")
    logger.info("=" * 80)

    # 测试 1: 发送消息
    task_id, send_success = test_kafka_producer()

    # 测试 2: 接收消息
    receive_success = test_kafka_consumer()

    # 输出结果
    logger.info("\n" + "=" * 80)
    logger.info("测试结果汇总")
    logger.info("=" * 80)
    logger.info(f"消息发送: {'✓ 成功' if send_success else '✗ 失败'}")
    logger.info(f"消息接收: {'✓ 成功' if receive_success else '✗ 失败'}")
    logger.info("=" * 80)

    if send_success and receive_success:
        logger.info("\n🎉 所有测试通过！Kafka 工作正常")
        return 0
    else:
        logger.error("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)