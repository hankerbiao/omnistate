#!/usr/bin/env python3
"""
DMLv4 Kafka 集成测试脚本

该脚本用于测试：
1. 向执行任务 API 发送任务创建请求
2. 验证 Kafka 是否收到了任务消息
3. 实时监控 Kafka 消息流

使用方法:
    python test_kafka_integration.py

环境变量:
    BACKEND_URL: 后端 API 地址 (默认: http://localhost:8000)
    KAFKA_BOOTSTRAP_SERVERS: Kafka 地址 (默认: localhost:9092)
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import List, Dict, Any

import requests
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('kafka_test.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 配置常量
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "10.17.154.252:9092")
TASK_TOPIC = "dmlv4.tasks"
RESULT_TOPIC = "dmlv4.results"

# 测试用例数据（这些用例ID需要在数据库中存在）
TEST_CASES = [
    {"case_id": "TC001"},
    {"case_id": "TC002"},
    {"case_id": "TC003"}
]

class KafkaMonitor:
    """Kafka 消息监控器"""

    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = [bootstrap_servers]
        self.consumer = None
        self.is_running = False
        self.messages = []

    def start(self):
        """启动 Kafka 消费者"""
        try:
            self.consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=f"kafka-test-monitor-{int(time.time())}",
                group_id=f"test-monitor-{int(time.time())}",
                value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                session_timeout_ms=30000,
                consumer_timeout_ms=1000
            )

            # 订阅主题
            self.consumer.subscribe([TASK_TOPIC, RESULT_TOPIC])
            self.is_running = True
            logger.info(f"Kafka 监控器已启动，订阅主题: {TASK_TOPIC}, {RESULT_TOPIC}")

            return True
        except Exception as e:
            logger.error(f"启动 Kafka 监控器失败: {e}")
            return False

    def stop(self):
        """停止 Kafka 消费者"""
        if self.consumer:
            self.consumer.close()
            self.is_running = False
            logger.info("Kafka 监控器已停止")

    def get_messages(self, timeout_ms: int = 5000) -> List[Dict[str, Any]]:
        """获取消息（阻塞方式）"""
        messages = []
        if not self.is_running or not self.consumer:
            return messages

        try:
            msg_pack = self.consumer.poll(timeout_ms=timeout_ms)
            for topic_partition, msg_list in msg_pack.items():
                for msg in msg_list:
                    messages.append({
                        'topic': msg.topic,
                        'partition': msg.partition,
                        'offset': msg.offset,
                        'key': msg.key,
                        'value': msg.value,
                        'timestamp': msg.timestamp
                    })
        except Exception as e:
            logger.error(f"获取 Kafka 消息失败: {e}")

        return messages

    def print_latest_messages(self, count: int = 5):
        """打印最新的 N 条消息"""
        messages = self.get_messages(timeout_ms=1000)
        if messages:
            logger.info(f"收到 {len(messages)} 条 Kafka 消息:")
            for msg in messages[-count:]:
                logger.info(
                    f"  主题: {msg['topic']}, "
                    f"分区: {msg['partition']}, "
                    f"偏移: {msg['offset']}, "
                    f"键: {msg['key']}\n"
                    f"  值: {json.dumps(msg['value'], indent=6, ensure_ascii=False)}"
                )


def check_backend_health() -> bool:
    """检查后端服务健康状态"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            logger.info("✓ 后端服务运行正常")
            return True
        else:
            logger.error(f"✗ 后端服务异常，状态码: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ 无法连接到后端服务: {e}")
        return False


def get_auth_token() -> str:
    """获取认证令牌（简化版本）"""
    # 注意：实际使用中需要根据认证系统获取有效的 JWT token
    # 这里为了测试，我们假设有一个测试用户

    # 尝试使用默认用户登录
    test_user = {
        "username": "admin",
        "password": "admin123"
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json=test_user,
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token') or data.get('data', {}).get('access_token')
            if token:
                logger.info("✓ 认证成功，获取到访问令牌")
                return token

        # 如果登录失败，尝试从环境变量读取
        token = os.getenv("TEST_TOKEN")
        if token:
            logger.info("✓ 使用环境变量中的测试令牌")
            return token

        logger.error("✗ 无法获取认证令牌")
        logger.error("  请设置 TEST_TOKEN 环境变量，或使用有效的测试用户凭据")
        return None

    except Exception as e:
        logger.error(f"✗ 认证失败: {e}")
        logger.error("  请设置 TEST_TOKEN 环境变量")
        return None


def create_execution_task(token: str, framework: str = "pytest") -> Dict[str, Any]:
    """创建执行任务"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "framework": framework,
        "trigger_source": "api_test",
        "callback_url": f"{BACKEND_URL}/api/v1/execution/callbacks/progress",
        "dut": {
            "hostname": "test-server-01",
            "platform": "x86_64",
            "memory": "32GB",
            "cpu": "Intel Xeon"
        },
        "cases": TEST_CASES,
        "runtime_config": {
            "timeout": 3600,
            "retry_times": 1,
            "parallel": False
        }
    }

    try:
        logger.info(f"发送任务创建请求到: {BACKEND_URL}/api/v1/execution/tasks/dispatch")
        logger.info(f"测试用例: {[c['case_id'] for c in TEST_CASES]}")

        response = requests.post(
            f"{BACKEND_URL}/api/v1/execution/tasks/dispatch",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 201:
            data = response.json()
            task_info = data.get('data', data)
            logger.info("✓ 任务创建成功")
            logger.info(f"  任务ID: {task_info.get('task_id')}")
            logger.info(f"  外部任务ID: {task_info.get('external_task_id')}")
            logger.info(f"  下发状态: {task_info.get('dispatch_status')}")
            logger.info(f"  任务状态: {task_info.get('overall_status')}")
            logger.info(f"  用例数量: {task_info.get('case_count')}")
            return task_info
        else:
            logger.error(f"✗ 任务创建失败，状态码: {response.status_code}")
            logger.error(f"  响应内容: {response.text}")
            return {}

    except Exception as e:
        logger.error(f"✗ 创建任务时发生错误: {e}")
        return {}


def query_task_status(token: str, task_id: str) -> Dict[str, Any]:
    """查询任务状态"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/execution/tasks/{task_id}",
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('data', data)
        else:
            logger.error(f"查询任务状态失败: {response.status_code}")
            return {}

    except Exception as e:
        logger.error(f"查询任务状态错误: {e}")
        return {}


def main():
    """主测试流程"""
    logger.info("=" * 80)
    logger.info("DMLv4 Kafka 集成测试开始")
    logger.info("=" * 80)

    # 步骤 1: 检查后端健康状态
    logger.info("\n[步骤 1/6] 检查后端服务健康状态")
    if not check_backend_health():
        logger.error("后端服务不可用，测试终止")
        return

    # 步骤 2: 获取认证令牌
    logger.info("\n[步骤 2/6] 获取认证令牌")
    token = get_auth_token()
    if not token:
        logger.error("无法获取认证令牌，测试终止")
        logger.error("请运行 'python scripts/create_user.py' 创建测试用户")
        return

    # 步骤 3: 启动 Kafka 监控器
    logger.info("\n[步骤 3/6] 启动 Kafka 监控器")
    monitor = KafkaMonitor(KAFKA_BOOTSTRAP_SERVERS)
    if not monitor.start():
        logger.error("Kafka 监控器启动失败，测试终止")
        return

    try:
        # 等待 Kafka 消费者初始化
        logger.info("等待 Kafka 消费者初始化...")
        time.sleep(2)

        # 步骤 4: 创建执行任务
        logger.info("\n[步骤 4/6] 创建执行任务")
        task_info = create_execution_task(token)
        if not task_info:
            logger.error("任务创建失败，测试终止")
            return

        task_id = task_info.get('task_id')
        external_task_id = task_info.get('external_task_id')

        # 步骤 5: 监控 Kafka 消息
        logger.info("\n[步骤 5/6] 监控 Kafka 消息")
        logger.info(f"等待任务消息到达主题 '{TASK_TOPIC}'...")
        logger.info("按 Ctrl+C 可随时停止监控\n")

        # 持续监控 30 秒
        deadline = time.time() + 30
        message_found = False

        while time.time() < deadline:
            try:
                messages = monitor.get_messages(timeout_ms=1000)

                if messages:
                    message_found = True
                    logger.info(f"✓ 收到 {len(messages)} 条消息:")

                    for msg in messages:
                        if msg['topic'] == TASK_TOPIC:
                            value = msg['value']
                            if value and value.get('task_id') == task_id:
                                logger.info("\n" + "=" * 80)
                                logger.info("✓✓✓ 找到目标任务消息！")
                                logger.info("=" * 80)
                                logger.info(f"主题: {msg['topic']}")
                                logger.info(f"任务ID: {value.get('task_id')}")
                                logger.info(f"任务类型: {value.get('task_type')}")
                                logger.info(f"消息来源: {value.get('source')}")
                                logger.info(f"优先级: {value.get('priority')}")
                                logger.info(f"任务数据:")
                                logger.info(json.dumps(value.get('task_data', {}), indent=2, ensure_ascii=False))
                                logger.info("=" * 80 + "\n")

                time.sleep(1)

            except KeyboardInterrupt:
                logger.info("\n用户中断监控")
                break

        if not message_found:
            logger.warning("\n⚠ 在 30 秒内未收到任务消息")
            logger.warning("可能的原因:")
            logger.warning("  1. Kafka 配置不正确")
            logger.warning("  2. 后端未正确发送消息到 Kafka")
            logger.warning("  3. 消费者组偏移量问题")
            logger.warning("  4. 网络连接问题")

        # 步骤 6: 查询任务状态
        logger.info("\n[步骤 6/6] 查询任务状态")
        status_info = query_task_status(token, task_id)
        if status_info:
            logger.info("✓ 任务状态查询成功")
            logger.info(f"  下发状态: {status_info.get('dispatch_status')}")
            logger.info(f"  任务状态: {status_info.get('overall_status')}")
            logger.info(f"  回调响应: {status_info.get('dispatch_response')}")

            # 显示用例统计
            stats = status_info.get('stats', {})
            if stats:
                logger.info("\n用例执行统计:")
                for status, count in stats.items():
                    logger.info(f"  {status}: {count}")

        # 输出测试摘要
        logger.info("\n" + "=" * 80)
        logger.info("测试摘要")
        logger.info("=" * 80)
        logger.info(f"任务ID: {task_id}")
        logger.info(f"外部任务ID: {external_task_id}")
        logger.info(f"Kafka 消息: {'✓ 收到' if message_found else '✗ 未收到'}")
        logger.info("=" * 80)

    finally:
        # 清理：停止 Kafka 监控器
        monitor.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
    except Exception as e:
        logger.error(f"\n测试过程中发生未处理的异常: {e}", exc_info=True)
        raise