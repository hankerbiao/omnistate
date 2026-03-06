#!/usr/bin/env python3
"""
Kafka 连接测试脚本
用于测试 Kafka broker 的连通性和基本功能
"""

import sys
import json
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError, NoBrokersAvailable, KafkaTimeoutError


def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")


def test_broker_connection(bootstrap_servers: str):
    """测试 broker 连接"""
    print_header("1. 测试 Broker 连接")

    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='test_connection_client',
            request_timeout_ms=5000
        )
        print(f"✅ 成功连接到 Kafka broker: {bootstrap_servers}")

        # 获取集群信息
        cluster_info = admin_client.describe_cluster()
        print(f"\n📊 集群信息:")
        print(f"   Cluster ID: {cluster_info.cluster_id}")
        print(f"   Controller: {cluster_info.controller}")
        print(f"   Broker 数量: {len(cluster_info.brokers)}")

        for broker_id, broker_info in cluster_info.brokers.items():
            print(f"   - Broker {broker_id}: {broker_info.host}:{broker_info.port}")

        admin_client.close()
        return True

    except NoBrokersAvailable as e:
        print(f"❌ 无法连接到 Kafka broker: {e}")
        print(f"\n🔍 可能的原因:")
        print(f"   1. Kafka 服务未启动")
        print(f"   2. 地址或端口错误: {bootstrap_servers}")
        print(f"   3. 网络连接问题")
        print(f"   4. 防火墙阻止连接")
        return False

    except Exception as e:
        print(f"❌ 连接测试失败: {e}")
        return False


def test_producer(bootstrap_servers: str, topic: str):
    """测试消息生产者"""
    print_header(f"2. 测试生产者 - Topic: {topic}")

    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id='test_producer',
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
            acks='all',
            retries=3,
            request_timeout_ms=10000
        )

        # 发送测试消息
        test_data = {
            'message_id': 'test_001',
            'content': 'Kafka 连接测试消息',
            'timestamp': '2026-03-06T10:00:00Z',
            'test_type': 'connection_test'
        }

        future = producer.send(topic, value=test_data)
        record_metadata = future.get(timeout=10)

        print(f"✅ 消息发送成功!")
        print(f"   Topic: {record_metadata.topic}")
        print(f"   Partition: {record_metadata.partition}")
        print(f"   Offset: {record_metadata.offset}")

        producer.close()
        return True

    except KafkaTimeoutError as e:
        print(f"❌ 发送消息超时: {e}")
        return False

    except KafkaError as e:
        print(f"❌ 发送消息失败: {e}")
        return False

    except Exception as e:
        print(f"❌ 生产者测试失败: {e}")
        return False


def test_consumer(bootstrap_servers: str, topic: str, timeout_ms: int = 5000):
    """测试消息消费者"""
    print_header(f"3. 测试消费者 - Topic: {topic}")

    try:
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            client_id='test_consumer',
            group_id='test_consumer_group',
            auto_offset_reset='latest',
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
            consumer_timeout_ms=timeout_ms
        )

        # 订阅 topic
        consumer.subscribe([topic])
        print(f"✅ 成功订阅 topic: {topic}")

        # 尝试消费消息
        print(f"\n🔄 等待消息 ({timeout_ms}ms)...")
        message_count = 0

        for message in consumer:
            message_count += 1
            print(f"\n📨 收到消息 {message_count}:")
            print(f"   Topic: {message.topic}")
            print(f"   Partition: {message.partition}")
            print(f"   Offset: {message.offset}")
            print(f"   Key: {message.key}")
            print(f"   Value: {message.value}")

            if message_count >= 5:  # 最多消费 5 条消息
                break

        if message_count == 0:
            print(f"⚠️  未收到任何消息（可能 topic 为空或消费者组未找到数据）")
        else:
            print(f"\n✅ 成功消费 {message_count} 条消息")

        consumer.close()
        return True

    except KafkaTimeoutError:
        print(f"⚠️  消费消息超时（topic 可能为空）")
        consumer.close()
        return False

    except Exception as e:
        print(f"❌ 消费者测试失败: {e}")
        try:
            consumer.close()
        except:
            pass
        return False


def create_topic_if_not_exists(bootstrap_servers: str, topic: str):
    """如果 topic 不存在则创建"""
    print_header(f"4. 检查/创建 Topic: {topic}")

    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='test_admin_client',
            request_timeout_ms=10000
        )

        # 检查 topic 是否存在
        metadata = admin_client.list_topics()
        if topic in metadata:
            print(f"✅ Topic '{topic}' 已存在")

            # 获取 topic 详细信息
            topic_desc = admin_client.describe_topics([topic])
            for desc in topic_desc:
                print(f"\n📋 Topic 详情:")
                print(f"   Name: {desc.name}")
                print(f"   Partitions: {len(desc.partitions)}")
                for partition in desc.partitions:
                    p_info = desc.partitions[partition]
                    print(f"   - Partition {partition}: Leader={p_info.leader}")

        else:
            print(f"ℹ️  Topic '{topic}' 不存在，正在创建...")

            # 创建 topic
            topic_config = NewTopic(
                name=topic,
                num_partitions=3,
                replication_factor=1
            )

            admin_client.create_topics([topic_config])
            print(f"✅ Topic '{topic}' 创建成功")

        admin_client.close()
        return True

    except Exception as e:
        print(f"❌ Topic 操作失败: {e}")
        try:
            admin_client.close()
        except:
            pass
        return False


def list_all_topics(bootstrap_servers: str):
    """列出所有 topics"""
    print_header("5. 列出所有 Topics")

    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='test_list_client',
            request_timeout_ms=5000
        )

        topics = admin_client.list_topics()
        print(f"📊 共有 {len(topics)} 个 topics:")

        for topic in sorted(topics):
            print(f"   - {topic}")

        admin_client.close()
        return True

    except Exception as e:
        print(f"❌ 列出 topics 失败: {e}")
        try:
            admin_client.close()
        except:
            pass
        return False


def main():
    """主函数"""
    print_header("Kafka 连接测试工具")
    print("这个脚本将测试 Kafka 的连接、生产、消费等功能")

    # 配置
    bootstrap_servers = "10.17.154.252:9092"
    test_topic = "test_connection_topic"

    results = {
        "broker_connection": False,
        "topic_creation": False,
        "producer": False,
        "consumer": False,
        "list_topics": False
    }

    # 1. 测试 broker 连接
    results["broker_connection"] = test_broker_connection(bootstrap_servers)

    if not results["broker_connection"]:
        print_header("❌ 连接失败")
        print("由于无法连接到 Kafka broker，测试终止")
        print("\n💡 建议:")
        print("1. 检查 Kafka 服务是否已启动")
        print("2. 验证地址和端口是否正确")
        print("3. 检查网络连接和防火墙")
        print("4. 查看 Kafka 日志: tail -f /path/to/kafka/logs/server.log")
        sys.exit(1)

    # 2. 创建 topic
    results["topic_creation"] = create_topic_if_not_exists(bootstrap_servers, test_topic)

    # 3. 测试生产者
    results["producer"] = test_producer(bootstrap_servers, test_topic)

    # 4. 测试消费者
    results["consumer"] = test_consumer(bootstrap_servers, test_topic)

    # 5. 列出所有 topics
    results["list_topics"] = list_all_topics(bootstrap_servers)

    # 总结
    print_header("测试结果总结")

    total_tests = len(results)
    passed_tests = sum(results.values())

    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        test_name_cn = {
            "broker_connection": "Broker 连接",
            "topic_creation": "Topic 创建",
            "producer": "生产者",
            "consumer": "消费者",
            "list_topics": "列出 Topics"
        }[test_name]
        print(f"   {test_name_cn}: {status}")

    print(f"\n📊 总计: {passed_tests}/{total_tests} 项测试通过")

    if passed_tests == total_tests:
        print("\n🎉 所有测试通过! Kafka 连接正常")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_tests - passed_tests} 项测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()