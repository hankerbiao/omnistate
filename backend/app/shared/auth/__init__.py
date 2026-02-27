"""鉴权工具模块

AI 友好注释说明：
- 对外暴露 JWT 相关方法与权限依赖。
- 其他模块可直接 import 使用。
"""
from .jwt_auth import create_access_token, decode_token, get_current_user, require_permission

__all__ = [
    "create_access_token",
    "decode_token",
    "get_current_user",
    "require_permission",
]
