"""系统配置敏感值加密与展示保护。"""
from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


ENCRYPTED_PREFIX = "enc:v1:"
MASKED_CONFIG_VALUE = "******"
_ENCRYPTION_KEY_ENV = "DML_SYSTEM_CONFIG_ENCRYPTION_KEY"


def is_encrypted_value(value: str) -> bool:
    return value.startswith(ENCRYPTED_PREFIX)


def encrypt_config_value(value: str) -> str:
    """使用环境变量提供的 Fernet 密钥加密非空敏感值。"""
    if not value or is_encrypted_value(value):
        return value
    key = os.getenv(_ENCRYPTION_KEY_ENV)
    if not key:
        raise RuntimeError(f"敏感配置写入需要设置 {_ENCRYPTION_KEY_ENV}")
    try:
        token = Fernet(key.encode("ascii")).encrypt(value.encode("utf-8")).decode("ascii")
    except (ValueError, TypeError) as exc:
        raise RuntimeError(f"{_ENCRYPTION_KEY_ENV} 不是有效的 Fernet 密钥") from exc
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_config_value(value: str) -> str:
    """解密新格式密文；兼容升级前已经存在的明文配置。"""
    if not is_encrypted_value(value):
        return value
    key = os.getenv(_ENCRYPTION_KEY_ENV)
    if not key:
        raise RuntimeError(f"读取敏感配置需要设置 {_ENCRYPTION_KEY_ENV}")
    try:
        return Fernet(key.encode("ascii")).decrypt(
            value[len(ENCRYPTED_PREFIX):].encode("ascii")
        ).decode("utf-8")
    except (InvalidToken, ValueError, TypeError) as exc:
        raise RuntimeError("敏感配置解密失败") from exc


def mask_config_value(value: str | None) -> str | None:
    """API 响应和历史记录固定返回掩码，不暴露是否为空。"""
    return MASKED_CONFIG_VALUE if value is not None else None
