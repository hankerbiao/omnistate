"""认证与权限检查。"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from ..domain.models import ApiKey, AuthenticatedKey
from ..infrastructure.repository import GatewayRepository


class GatewayAuth:
    """校验开放平台 API Key。"""

    def __init__(self, repository: GatewayRepository) -> None:
        self._repository = repository

    def authenticate(self, request: Request) -> AuthenticatedKey:
        token = _extract_bearer(request.headers.get("authorization"))
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer API key")

        key = self._repository.find_key_by_plaintext(token)
        if not key or key.status != "active":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key")
        return AuthenticatedKey(key=key, presented_token=token)

    @staticmethod
    def require_scope(key: ApiKey, scope: str) -> None:
        if scope not in key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"API key requires scope: {scope}"
            )


def _extract_bearer(value: str | None) -> str:
    if not value:
        return ""
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return ""
    return token.strip()
