import json
from fastapi import HTTPException
import pytest

from app.shared.auth import jwt_auth
from app.shared.db.config import settings


def _build_token_with_payload(payload_b64: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = jwt_auth._b64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = jwt_auth._sign_hs256(signing_input, settings.JWT_SECRET_KEY)
    return f"{header_b64}.{payload_b64}.{signature}"


@pytest.mark.parametrize(
    "payload_b64",
    [
        "!!",  # 非法 base64
        jwt_auth._b64url_encode(b"not-json"),  # 非法 JSON
        jwt_auth._b64url_encode(b"\xff"),  # 非 UTF-8
    ],
)
def test_decode_token_invalid_payload_returns_401(payload_b64: str) -> None:
    token = _build_token_with_payload(payload_b64)

    with pytest.raises(HTTPException) as exc_info:
        jwt_auth.decode_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "invalid token"
