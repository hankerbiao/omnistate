"""鉴权工具模块

AI 友好注释说明：
- 对外暴露 JWT 相关方法、权限依赖与密码工具。
- 其他模块可直接 import 使用。
"""
from .jwt_auth import (
    create_access_token,
    decode_token,
    get_current_user,
    require_permission,
    require_any_permission,
)
from .password import hash_password, verify_password

__all__ = [
    "create_access_token",
    "decode_token",
    "get_current_user",
    "require_permission",
    "require_any_permission",
    "hash_password",
    "verify_password",
]
