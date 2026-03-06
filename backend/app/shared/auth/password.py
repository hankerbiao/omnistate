"""密码哈希与校验工具
"""
from __future__ import annotations

import base64
import os
import hashlib
import hmac
from typing import Tuple


_ITERATIONS = 200_000
_KEY_LEN = 32


def hash_password(password: str) -> Tuple[str, str]:
    """生成密码哈希

    返回 (salt_b64, hash_b64)
    """
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
        dklen=_KEY_LEN,
    )
    return base64.b64encode(salt).decode("utf-8"), base64.b64encode(dk).decode("utf-8")


def verify_password(password: str, salt_b64: str, hash_b64: str) -> bool:
    """校验密码是否匹配"""
    salt = base64.b64decode(salt_b64.encode("utf-8"))
    expected = base64.b64decode(hash_b64.encode("utf-8"))
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
        dklen=_KEY_LEN,
    )
    return hmac.compare_digest(dk, expected)
