"""Redis 模块 Pydantic 模式定义。"""

from pydantic import BaseModel


class KeyValueResponse(BaseModel):
    """查询单个 Key 的响应。"""

    key: str
    value: str | None = None
    ttl: int = -1


class PublishRequest(BaseModel):
    """发布消息请求。"""

    message: str
    channel: str = "dmlv4:events"


class PingResponse(BaseModel):
    """Ping 健康检查响应。"""

    status: str = "ok"
    latency_ms: float = 0.0
