"""Redis 连接管理器。

全局单例，应用启动后第一次调用时自动初始化 Sentinel 连接池。
业务代码通过 `redis_conn`（写）和 `redis_read`（读）直接使用。
"""

from __future__ import annotations

import queue
import threading
from typing import Any

from redis.sentinel import Sentinel

from app.modules.redis.domain.constants import DEFAULT_EVENT_CHANNEL, KEY_NAMESPACE, PUBLISH_QUEUE_MAXSIZE
from app.modules.redis.domain.exceptions import RedisConnectionError
from app.shared.core.logger import log as logger

# ── 连接池参数（按并发量调整 max_connections）────────────────────────
_POOL_KWARGS: dict[str, Any] = {
    "socket_timeout": 2,
    "username": "dmlv4",
    "password": "7GipPaqKHQNn37Vb",
    "db": 0,
    "decode_responses": True,
    "protocol": 2,
    "max_connections": 100,
    "retry_on_timeout": True,
}

SENTINEL_HOSTS: list[tuple[str, int]] = [
    ("10.17.152.51", 26379),
    ("10.17.151.56", 26379),
    ("10.17.152.46", 26379),
]
MASTER_NAME = "redis_master"


class RedisManager:
    """全局单例：整个应用只初始化一次 Sentinel 与连接池。"""

    _instance: RedisManager | None = None
    _master: Any = None
    _slave: Any = None

    def __new__(cls, *args: Any, **kwargs: Any) -> RedisManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if RedisManager._master is not None:
            return

        try:
            self.sentinel = Sentinel(
                SENTINEL_HOSTS,
                socket_timeout=0.5,
                sentinel_kwargs={"socket_timeout": 0.5},
                retry_on_timeout=True,
            )
            RedisManager._master = self.sentinel.master_for(MASTER_NAME, **_POOL_KWARGS)
            RedisManager._slave = self.sentinel.slave_for(MASTER_NAME, **_POOL_KWARGS)
            RedisManager._master.ping()
            logger.success("Redis 连接池初始化成功")
        except Exception as exc:
            logger.exception(f"Redis 连接失败: {exc}")
            raise RedisConnectionError(f"Redis 连接失败: {exc}") from exc

    @property
    def master(self) -> Any:
        return RedisManager._master

    @property
    def slave(self) -> Any:
        return RedisManager._slave


# ── 模块级单例 — 应用启动时第一次引用时自动初始化 ──────────────────
redis_mgr = RedisManager()
redis_conn = redis_mgr.master   # 写操作
redis_read = redis_mgr.slave    # 读操作（可路由到从节点）


def build_key(domain: str, entity: str, key_id: str) -> str:
    """构建符合命名规范的 Redis Key。

    Args:
        domain: 业务域，如 "cache"、"user"、"order"
        entity: 实体名，如 "session"、"profile"
        key_id: 实体标识，如用户 ID、订单 ID

    Returns:
        格式: dmlv4:{domain}:{entity}:{id}
    """
    return f"{KEY_NAMESPACE}:{domain}:{entity}:{key_id}"


# ── 异步 Pub/Sub 发布（后台线程消费，不阻塞主业务线程）─────────────
_publish_queue: queue.Queue = queue.Queue(maxsize=PUBLISH_QUEUE_MAXSIZE)


def _bg_publisher() -> None:
    """后台线程：独立长连接消费发布队列。"""
    conn = redis_mgr.master
    while True:
        try:
            channel, message = _publish_queue.get()
            conn.publish(channel, message)
        except Exception:
            pass


threading.Thread(target=_bg_publisher, daemon=True).start()


def publish_event(message: str, channel: str = DEFAULT_EVENT_CHANNEL) -> None:
    """非阻塞发布消息；队列满时丢弃，避免堵死主进程。"""
    try:
        _publish_queue.put_nowait((channel, message))
    except queue.Full:
        logger.warning("Redis 发布队列已满，消息已丢弃")
