"""JWT 鉴权依赖"""
from __future__ import annotations

import binascii
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.shared.config import get_settings
from app.shared.context import set_operation_context
from app.modules.auth.repository.models import UserDoc, RoleDoc, PermissionDoc


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
    _jwt = get_settings().jwt
    expire = now + timedelta(minutes=expires_minutes or _jwt.expire_minutes)

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": _jwt.issuer,
        "aud": _jwt.audience,
    }

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature_b64 = _sign_hs256(signing_input, _jwt.secret_key)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_token(token: str) -> Dict[str, Any]:
    """校验并解析 JWT，返回 payload"""
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = _sign_hs256(signing_input, get_settings().jwt.secret_key)
    if not hmac.compare_digest(signature_b64, expected_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (
            binascii.Error,
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    # 基本字段校验
    now_ts = int(datetime.now(timezone.utc).timestamp())
    try:
        exp_ts = int(payload["exp"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")

    if now_ts >= exp_ts:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired")
    _jwt = get_settings().jwt
    if payload.get("iss") != _jwt.issuer:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid issuer")
    if payload.get("aud") != _jwt.audience:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid audience")

    return payload


# ===== FastAPI 依赖 =====

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """解析 JWT 并返回用户信息

    返回结构为 dict，包含 id/user_id/username/role_ids 等字段。
    """
    # 正式模式：必须提供有效 token
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

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

    # 设置操作上下文，供日志系统使用
    set_operation_context(
        user_id=str(user.user_id),
        username=getattr(user, "username", "") or getattr(user, "display_name", ""),
        role_ids=[str(r) for r in (data.get("role_ids") or [])],
    )

    return data


async def get_permissions_by_ids(perm_ids: List[str]) -> List[str]:
    """根据 perm_id 列表解析权限码并排序。"""
    if not perm_ids:
        return []
    perms = await PermissionDoc.find({"perm_id": {"$in": list(set(perm_ids))}}).to_list()
    return sorted({perm.code for perm in perms})


async def get_user_permissions(user_id: str) -> List[str]:
    """根据 user_id 解析权限码列表（角色权限 ∪ 用户额外权限）"""
    user = await UserDoc.find_one(UserDoc.user_id == user_id)
    if not user:
        return []
    role_codes = await get_permissions_by_role_ids(user.role_ids or [])
    extra_codes = await get_permissions_by_ids(user.extra_permission_ids or [])
    return sorted(set(role_codes) | set(extra_codes))


async def get_permissions_by_role_ids(role_ids: List[str]) -> List[str]:
    """根据角色列表解析权限码并去重排序。"""
    if not role_ids:
        return []

    # 兼容 ROLE_ 前缀差异（如 ROLE_TPM / TPM），避免因命名不一致导致权限丢失
    normalized_role_ids = set()
    for role_id in role_ids:
        rid = str(role_id).strip()
        if not rid:
            continue
        normalized_role_ids.add(rid)
        if rid.startswith("ROLE_"):
            normalized_role_ids.add(rid[5:])
        else:
            normalized_role_ids.add(f"ROLE_{rid}")

    roles = await RoleDoc.find({"role_id": {"$in": list(normalized_role_ids)}}).to_list()
    perm_ids: List[str] = []
    for role in roles:
        perm_ids.extend(role.permission_ids)
    if not perm_ids:
        return []
    perms = await PermissionDoc.find({"perm_id": {"$in": list(set(perm_ids))}}).to_list()
    return sorted({perm.code for perm in perms})


def _normalize_role_id(role_id: str) -> str:
    normalized = role_id.strip().upper()
    if normalized.startswith("ROLE_"):
        normalized = normalized[5:]
    return normalized


def is_admin_role(role_ids: List[str]) -> bool:
    return any(_normalize_role_id(str(rid)) == "ADMIN" for rid in role_ids)


def require_permission(permission_code: str) -> Callable:
    """权限校验依赖：要求用户拥有指定权限。"""
    if not permission_code:
        raise ValueError("permission_code must not be empty")
    return require_any_permission([permission_code])


def require_any_permission(permission_codes: List[str]) -> Callable:
    """权限校验依赖：要求用户至少拥有一个权限。"""
    required = {code for code in permission_codes if code}
    if not required:
        raise ValueError("permission_codes must not be empty")

    async def _checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        if is_admin_role(current_user.get("role_ids", [])):
            return
        perms = set(await get_user_permissions(current_user["user_id"]))
        if perms.isdisjoint(required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="permission denied",
            )

    return _checker
