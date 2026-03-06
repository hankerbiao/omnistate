"""SDK 工具函数"""

import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional


def generate_event_id() -> str:
    """生成唯一事件ID（UUID v4）"""
    return str(uuid.uuid4())


def generate_timestamp() -> int:
    """生成当前时间戳（Unix秒）"""
    return int(time.time())


def compute_signature(secret: str, timestamp: str, event_id: str, raw_body: bytes) -> str:
    """计算HMAC-SHA256签名

    Args:
        secret: 签名密钥
        timestamp: 时间戳字符串
        event_id: 事件ID
        raw_body: 原始请求体

    Returns:
        十六进制签名字符串
    """
    signing_string = f"{timestamp}\n{event_id}\n".encode("utf-8") + raw_body
    signature = hmac.new(
        secret.encode("utf-8"),
        signing_string,
        hashlib.sha256
    ).hexdigest()
    return signature


def validate_timestamp(timestamp: int, window_seconds: int = 300) -> bool:
    """验证时间戳是否在允许窗口内

    Args:
        timestamp: 待验证的时间戳
        window_seconds: 时间窗口（秒），默认5分钟

    Returns:
        是否在允许范围内
    """
    now = int(time.time())
    return abs(now - timestamp) <= window_seconds


def validate_status(value: str, allowed_values: list) -> bool:
    """验证状态值是否有效

    Args:
        value: 待验证的状态值
        allowed_values: 允许的状态值列表

    Returns:
        是否为有效状态
    """
    return value.upper() in [v.upper() for v in allowed_values]


def ensure_event_time(event_time: Optional[datetime] = None) -> datetime:
    """确保事件时间有效

    Args:
        event_time: 传入的事件时间，如果为None则使用当前时间

    Returns:
        标准化的事件时间（UTC）
    """
    if event_time is None:
        return datetime.now(timezone.utc)
    if event_time.tzinfo is None:
        # 如果没有时区信息，假设为UTC
        return event_time.replace(tzinfo=timezone.utc)
    return event_time.astimezone(timezone.utc)


def safe_serialize(obj: Any) -> str:
    """安全地序列化对象为JSON字符串

    Args:
        obj: 待序列化的对象

    Returns:
        JSON字符串
    """
    def json_serializer(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    return json.dumps(obj, default=json_serializer, ensure_ascii=False)


def create_progress_headers(
    framework_id: str,
    event_id: str,
    timestamp: int,
    signature: str
) -> Dict[str, str]:
    """创建进度回调的HTTP头

    Args:
        framework_id: 框架标识
        event_id: 事件ID
        timestamp: 时间戳
        signature: 签名

    Returns:
        HTTP头字典
    """
    return {
        "X-Framework-Id": framework_id,
        "X-Event-Id": event_id,
        "X-Timestamp": str(timestamp),
        "X-Signature": signature,
        "Content-Type": "application/json",
    }


def sanitize_error_message(message: str) -> str:
    """清理错误消息，移除敏感信息

    Args:
        message: 原始错误消息

    Returns:
        清理后的错误消息
    """
    # 移除可能的密钥信息
    sensitive_patterns = [
        "secret", "password", "token", "key", "signature",
        "authorization", "auth", "credential"
    ]

    message_lower = message.lower()
    for pattern in sensitive_patterns:
        if pattern in message_lower:
            return "Authentication or validation failed"

    return message