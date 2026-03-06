#!/usr/bin/env python3
"""
快速 Kafka 连接检查脚本
"""

from kafka import KafkaAdminClient
from kafka.errors import NoBrokersAvailable

def quick_test():
    """快速测试 Kafka 连接"""
    print("正在测试 Kafka 连接...")
    print(f"Bootstrap servers: 10.17.154.252:9092\n")

    try:
        # 尝试连接
        client = KafkaAdminClient(
            bootstrap_servers="10.17.154.252:9092",
            client_id="quick_test",
            request_timeout_ms=5000
        )

        # 获取集群信息
        cluster_info = client.describe_cluster()
        print(f"✅ 连接成功!")
        print(f"   Cluster ID: {cluster_info.cluster_id}")
        print(f"   Brokers: {len(cluster_info.brokers)}")
        print(f"   Controller: {cluster_info.controller}")

        # 列出 topics
        topics = client.list_topics()
        print(f"\n📊 Topics 数量: {len(topics)}")

        client.close()
        return True

    except NoBrokersAvailable:
        print("❌ 连接失败: NoBrokersAvailable")
        print("   Kafka broker 不可用")
        print("\n💡 检查事项:")
        print("   1. Kafka 服务是否启动")
        print("   2. 网络连接")
        print("   3. 地址/端口是否正确")
        return False

    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = quick_test()
    sys.exit(0 if success else 1)