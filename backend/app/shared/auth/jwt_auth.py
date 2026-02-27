"""JWT 鉴权依赖（可直接用于 FastAPI）

AI 友好注释说明：
- 本文件提供可用的 JWT 编解码与权限校验依赖。
- 使用 HS256（对称密钥）实现，无需额外第三方库。
- 如需更复杂的授权策略，可在此基础上扩展。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.shared.db.config import settings
from app.modules.auth.repository.models import UserDoc, RoleDoc, PermissionDoc


# ===== JWT 基础工具 =====

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign_hs256(message: bytes, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64url_encode(signature)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    """创建 JWT

    subject 通常为 user_id。
    expires_minutes 为 token 有效期（分钟），为空则使用配置默认值。
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES)

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature_b64 = _sign_hs256(signing_input, settings.JWT_SECRET_KEY)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_token(token: str) -> Dict[str, Any]:
    """校验并解析 JWT，返回 payload"""
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = _sign_hs256(signing_input, settings.JWT_SECRET_KEY)
    if not hmac.compare_digest(signature_b64, expected_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    payload = json.loads(_b64url_decode(payload_b64))

    # 基本字段校验
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if payload.get("exp") is None or now_ts >= int(payload["exp"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired")
    if payload.get("iss") != settings.JWT_ISSUER:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid issuer")
    if payload.get("aud") != settings.JWT_AUDIENCE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid audience")

    return payload


# ===== FastAPI 依赖 =====

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """解析 JWT 并返回用户信息

    返回结构为 dict，包含 id/user_id/username/role_ids 等字段。
    """
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    user = await UserDoc.find_one(UserDoc.user_id == user_id)
    if not user or user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user disabled")

    data = user.model_dump()
    data["id"] = str(user.id)
    return data


async def get_user_permissions(user_id: str) -> List[str]:
    """根据 user_id 解析权限码列表（Role → Permission）"""
    user = await UserDoc.find_one(UserDoc.user_id == user_id)
    if not user:
        return []
    roles = await RoleDoc.find(RoleDoc.role_id.in_(user.role_ids)).to_list()
    perm_ids: List[str] = []
    for role in roles:
        perm_ids.extend(role.permission_ids)
    if not perm_ids:
        return []
    perms = await PermissionDoc.find(PermissionDoc.perm_id.in_(list(set(perm_ids)))).to_list()
    return [perm.code for perm in perms]


def require_permission(permission_code: str) -> Callable:
    """权限校验依赖：要求用户拥有指定权限"""

    async def _checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        perms = await get_user_permissions(current_user["user_id"])
        if permission_code not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="permission denied",
            )

    return _checker
