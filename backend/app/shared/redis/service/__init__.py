"""Redis 连接管理器。

全局单例，由 FastAPI lifespan 事件初始化 Sentinel 连接池。
业务代码通过 `redis_conn`（写）和 `redis_read`（读）直接使用。
"""

from __future__ import annotations

import json
import queue
import socket
import threading
import time
from typing import Any

from redis.sentinel import Sentinel

from app.shared.redis.service.constants import DEFAULT_EVENT_CHANNEL, KEY_NAMESPACE, PUBLISH_QUEUE_MAXSIZE
from app.shared.redis.service.exceptions import RedisConnectionError
from app.shared.config import get_settings
from app.shared.core.logger import log as logger


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
            cfg = get_settings().redis
            sentinel_hosts: list[tuple[str, int]] = []
            for host_str in cfg.sentinel_hosts:
                parts = host_str.split(":")
                host = parts[0]
                port = int(parts[1]) if len(parts) > 1 else 26379
                sentinel_hosts.append((host, port))

            sentinel_timeout = cfg.sentinel_socket_timeout
            pool_kwargs: dict[str, Any] = {
                "socket_timeout": cfg.socket_timeout,
                "username": cfg.username or None,
                "password": cfg.password or None,
                "db": cfg.db,
                "decode_responses": True,
                "protocol": cfg.protocol,
                "max_connections": cfg.max_connections,
                "retry_on_timeout": cfg.retry_on_timeout,
            }

            self.sentinel = Sentinel(
                sentinel_hosts,
                socket_timeout=sentinel_timeout,
                sentinel_kwargs={"socket_timeout": sentinel_timeout},
                retry_on_timeout=cfg.retry_on_timeout,
            )
            RedisManager._master = self.sentinel.master_for(cfg.master_name, **pool_kwargs)
            RedisManager._slave = self.sentinel.slave_for(cfg.master_name, **pool_kwargs)
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


# ── 模块级引用（初始为 None，由 lifespan 触发初始化）───────────────
redis_mgr: RedisManager | None = None
redis_conn: Any = None
redis_read: Any = None

# ── 发布队列（独立于连接池初始化，可以提前创建）──────────────────
_publish_queue: queue.Queue = queue.Queue(maxsize=PUBLISH_QUEUE_MAXSIZE)
_publish_thread: threading.Thread | None = None


def init_redis() -> None:
    """由 FastAPI lifespan 调用，完成 Sentinel 连接池和后台线程初始化。"""
    global redis_mgr, redis_conn, redis_read, _publish_thread

    if redis_conn is not None:
        return

    redis_mgr = RedisManager()
    redis_conn = redis_mgr.master
    redis_read = redis_mgr.slave

    _publish_thread = threading.Thread(target=_bg_publisher, daemon=True)
    _publish_thread.start()
    logger.info("Redis 后台发布线程已启动")

    # 注册服务实例并启动心跳续期
    register_service()
    _start_heartbeat()


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


def _bg_publisher() -> None:
    """后台线程：独立长连接消费发布队列。"""
    import app.shared.redis.service as svc
    while True:
        try:
            channel, message = _publish_queue.get()
            svc.redis_conn.publish(channel, message)
        except Exception as exc:
            logger.warning(f"Redis 发布失败: {exc}")


def publish_event(message: str, channel: str = DEFAULT_EVENT_CHANNEL) -> None:
    """非阻塞发布消息；队列满时丢弃，避免堵死主进程。"""
    try:
        _publish_queue.put_nowait((channel, message))
    except queue.Full:
        logger.warning("Redis 发布队列已满，消息已丢弃")


# ── 服务注册心跳续期 ──────────────────────────────────────────────

_heartbeat_thread: threading.Thread | None = None
_heartbeat_stop = threading.Event()


def _heartbeat_loop() -> None:
    """每分钟更新一次服务注册信息（含 IP、端口、状态）。"""
    while not _heartbeat_stop.is_set():
        _heartbeat_stop.wait(timeout=60)  # 1 分钟
        if _heartbeat_stop.is_set():
            break
        try:
            import app.shared.redis.service as svc
            cfg = get_settings()
            service_name = cfg.app.service_name
            host = _get_local_ip()
            port = cfg.app.port
            instance_id = f"{service_name}@{host}:{port}"
            ttl_sec = 600  # 10 分钟过期，心跳 1 分钟续一次足够

            info = {
                "service_name": service_name,
                "host": host,
                "port": port,
                "instance_id": instance_id,
                "status": "UP",
            }
            logger.debug("Redis heartbeat: key={} info={}", f"{SERVICE_REGISTRY_KEY}:{service_name}", info)
            svc.redis_conn.setex(
                f"{SERVICE_REGISTRY_KEY}:{service_name}",
                ttl_sec,
                json.dumps(info),
            )
        except Exception:
            pass  # 心跳失败下次重试


def _start_heartbeat() -> None:
    """启动后台心跳线程。"""
    global _heartbeat_thread
    if _heartbeat_thread is not None:
        return
    _heartbeat_stop.clear()
    _heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    _heartbeat_thread.start()
    logger.info("Redis 服务心跳线程已启动")


def stop_heartbeat() -> None:
    """停止后台心跳线程。"""
    _heartbeat_stop.set()


# ── 服务注册/发现（将本服务实例信息上报到 Redis）───────────────────

SERVICE_REGISTRY_KEY: str = get_settings().redis.service_registry_key


def _get_local_ip() -> str:
    """获取本机内网 IP（优先取非 loopback 地址）。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("10.0.0.1", 80))  # 不需要真正可达
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def register_service() -> None:
    """向 Redis 注册本服务实例信息，供其他服务发现。"""
    if redis_conn is None:
        logger.warning("Redis 未初始化，跳过服务注册")
        return

    cfg = get_settings()
    service_name = cfg.app.service_name
    host = _get_local_ip()
    port = cfg.app.port
    instance_id = f"{service_name}@{host}:{port}"
    ttl_sec = 600  # 10 分钟过期，由定时心跳续期

    info = {
        "service_name": service_name,
        "host": host,
        "port": port,
        "instance_id": instance_id,
        "status": "UP",
        "registered_at": int(time.time()),
    }
    logger.debug("Redis register: key={} info={}", f"{SERVICE_REGISTRY_KEY}:{service_name}", info)

    try:
        redis_conn.setex(
            f"{SERVICE_REGISTRY_KEY}:{service_name}",
            ttl_sec,
            json.dumps(info),
        )
        logger.success(f"服务实例已注册到 Redis: {service_name}")
    except Exception as exc:
        logger.warning(f"服务注册到 Redis 失败: {exc}")


def unregister_service() -> None:
    """从 Redis 注销本服务实例。"""
    if redis_conn is None:
        return

    cfg = get_settings()
    service_name = cfg.app.service_name

    try:
        redis_conn.delete(f"{SERVICE_REGISTRY_KEY}:{service_name}")
        logger.info(f"服务实例已从 Redis 注销: {service_name}")
    except Exception as exc:
        logger.warning(f"服务从 Redis 注销失败: {exc}")
