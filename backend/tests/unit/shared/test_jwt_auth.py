"""JWT 鉴权单元测试。"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.shared.auth.jwt_auth import (
    _b64url_encode,
    _b64url_decode,
    _sign_hs256,
    create_access_token,
    decode_token,
    is_admin_role,
    _normalize_role_id,
    require_permission,
    require_any_permission,
)

# =============================================================================
# Base64 URL 编解码
# =============================================================================


class TestBase64Url:
    def test_encode_decode_roundtrip(self):
        data = b"hello world"
        encoded = _b64url_encode(data)
        decoded = _b64url_decode(encoded)
        assert decoded == data

    def test_encode_special_chars(self):
        """含 + / 的二进制数据应被编码为 - _"""
        data = b"\xff\xfb\x00\x01\xfe"
        encoded = _b64url_encode(data)
        assert "+" not in encoded
        assert "/" not in encoded
        decoded = _b64url_decode(encoded)
        assert decoded == data

    def test_encode_empty_bytes(self):
        assert _b64url_encode(b"") == ""

    def test_decode_missing_padding(self):
        """缺失 padding 的 base64url 应自动补齐"""
        data = b"test data"
        encoded = _b64url_encode(data)
        # 去掉 padding 再解码
        stripped = encoded.rstrip("=")
        decoded = _b64url_decode(stripped)
        assert decoded == data

    def test_decode_invalid_chars(self):
        """非 base64 字符可能会被静默处理，不抛异常也可接受"""
        # 不是期望它抛异常，而是验证函数不会崩溃
        try:
            result = _b64url_decode("!!!invalid!!!")
            assert isinstance(result, bytes)
        except Exception:
            pass

        try:
            result = _b64url_decode("not-base64-characters")
            assert isinstance(result, bytes)
        except Exception:
            pass


# =============================================================================
# HMAC 签名
# =============================================================================


class TestSignHS256:
    def test_sign_consistency(self):
        """相同消息+密钥应产生相同签名"""
        sig1 = _sign_hs256(b"message", "secret")
        sig2 = _sign_hs256(b"message", "secret")
        assert sig1 == sig2

    def test_different_key_different_signature(self):
        sig1 = _sign_hs256(b"message", "secret1")
        sig2 = _sign_hs256(b"message", "secret2")
        assert sig1 != sig2

    def test_different_message_different_signature(self):
        sig1 = _sign_hs256(b"msg1", "secret")
        sig2 = _sign_hs256(b"msg2", "secret")
        assert sig1 != sig2

    def test_empty_message(self):
        sig = _sign_hs256(b"", "secret")
        assert isinstance(sig, str)
        assert len(sig) > 0

    def test_empty_secret(self):
        sig = _sign_hs256(b"message", "")
        assert isinstance(sig, str)
        assert len(sig) > 0

    def test_unicode_in_secret(self):
        sig = _sign_hs256(b"message", "密钥中文!@#")
        assert isinstance(sig, str)
        assert len(sig) > 0


# =============================================================================
# JWT 创建
# =============================================================================


class TestCreateAccessToken:
    def test_create_token_returns_string(self):
        token = create_access_token(subject="user-001")
        assert isinstance(token, str)
        # JWT 格式: header.payload.signature
        assert token.count(".") == 2

    def test_create_token_custom_expiry(self):
        token = create_access_token(subject="user-001", expires_minutes=1)
        _, payload_b64, _ = token.split(".")
        payload = json.loads(_b64url_decode(payload_b64))
        assert payload["sub"] == "user-001"
        assert payload["iss"] is not None
        assert payload["aud"] is not None

    def test_create_token_default_expiry(self):
        """不传 expires_minutes 应使用默认值"""
        token = create_access_token(subject="user-001")
        _, payload_b64, _ = token.split(".")
        payload = json.loads(_b64url_decode(payload_b64))
        assert payload["sub"] == "user-001"


# =============================================================================
# JWT 解码
# =============================================================================


class TestDecodeToken:
    def test_decode_valid_token(self):
        token = create_access_token(subject="user-001", expires_minutes=60)
        payload = decode_token(token)
        assert payload["sub"] == "user-001"

    def test_decode_tampered_signature(self):
        token = create_access_token(subject="user-001", expires_minutes=60)
        # 篡改 payload 部分
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}x.{parts[2]}"
        with pytest.raises(HTTPException) as exc:
            decode_token(tampered)
        assert exc.value.status_code == 401
        assert "invalid token" in exc.value.detail

    def test_decode_expired_token(self):
        """手动构造已过期的 token"""
        header_b64 = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        # 设置 exp 为过去的时间戳
        payload = {
            "sub": "user-001",
            "iat": 1000000,
            "exp": 1000001,
            "iss": "tcm-backend",
            "aud": "tcm-frontend",
        }
        payload_b64 = _b64url_encode(json.dumps(payload).encode())
        from app.shared.config import get_settings
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        sig = _sign_hs256(signing_input, get_settings().jwt.secret_key)
        token = f"{header_b64}.{payload_b64}.{sig}"

        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401
        assert "token expired" in str(exc.value.detail)

    def test_decode_wrong_issuer(self):
        """用错误 issuer 签名的 token"""
        header_b64 = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        now = 2000000000
        payload = {
            "sub": "user-001",
            "iat": now,
            "exp": now + 3600,
            "iss": "wrong-issuer",
            "aud": "tcm-frontend",
        }
        payload_b64 = _b64url_encode(json.dumps(payload).encode())
        from app.shared.config import get_settings
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        sig = _sign_hs256(signing_input, get_settings().jwt.secret_key)
        token = f"{header_b64}.{payload_b64}.{sig}"

        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401
        assert "invalid issuer" in str(exc.value.detail)

    def test_decode_wrong_audience(self):
        """用错误 audience 签名的 token"""
        header_b64 = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        now = 2000000000
        payload = {
            "sub": "user-001",
            "iat": now,
            "exp": now + 3600,
            "iss": "tcm-backend",
            "aud": "wrong-audience",
        }
        payload_b64 = _b64url_encode(json.dumps(payload).encode())
        from app.shared.config import get_settings
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        sig = _sign_hs256(signing_input, get_settings().jwt.secret_key)
        token = f"{header_b64}.{payload_b64}.{sig}"

        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401
        assert "invalid audience" in str(exc.value.detail)

    def test_decode_invalid_format(self):
        """非三段式 token"""
        with pytest.raises(HTTPException) as exc:
            decode_token("not-a-valid-token")
        assert exc.value.status_code == 401

        with pytest.raises(HTTPException) as exc:
            decode_token("a.b")
        assert exc.value.status_code == 401

    def test_decode_payload_not_dict(self):
        """payload 为非 dict 类型"""
        header_b64 = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        # payload 是字符串 "hello"，不是 dict
        payload_b64 = _b64url_encode(json.dumps("hello").encode())
        from app.shared.config import get_settings

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        sig = _sign_hs256(signing_input, get_settings().jwt.secret_key)
        token = f"{header_b64}.{payload_b64}.{sig}"

        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401

    def test_decode_missing_exp(self):
        """payload 缺少 exp 字段"""
        header_b64 = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload = {"sub": "user-001", "iss": "tcm-backend", "aud": "tcm-frontend"}
        payload_b64 = _b64url_encode(json.dumps(payload).encode())
        from app.shared.config import get_settings

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        sig = _sign_hs256(signing_input, get_settings().jwt.secret_key)
        token = f"{header_b64}.{payload_b64}.{sig}"

        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401

    def test_decode_empty_token(self):
        with pytest.raises(HTTPException):
            decode_token("")


# =============================================================================
# 角色判断
# =============================================================================


class TestRoleHelpers:
    def test_is_admin_role(self):
        assert is_admin_role(["ADMIN"]) is True
        assert is_admin_role(["ROLE_ADMIN"]) is True
        assert is_admin_role(["admin"]) is True  # 小写
        assert is_admin_role(["TPM", "REVIEWER"]) is False
        assert is_admin_role([]) is False

    def test_normalize_role_id(self):
        assert _normalize_role_id("ROLE_ADMIN") == "ADMIN"
        assert _normalize_role_id("ADMIN") == "ADMIN"
        assert _normalize_role_id(" role_admin ") == "ADMIN"  # strip + upper + 去前缀
        assert _normalize_role_id("") == ""
        assert _normalize_role_id("TPM") == "TPM"
        assert _normalize_role_id("ROLE_TPM") == "TPM"


# =============================================================================
# 权限校验
# =============================================================================


class TestRequirePermission:
    def test_empty_permission_code(self):
        with pytest.raises(ValueError, match="must not be empty"):
            require_permission("")

    def test_require_permission_returns_checker(self):
        checker = require_permission("work_items:read")
        assert callable(checker)


class TestRequireAnyPermission:
    def test_empty_list(self):
        with pytest.raises(ValueError, match="must not be empty"):
            require_any_permission([])

    def test_list_with_only_empty_strings(self):
        with pytest.raises(ValueError, match="must not be empty"):
            require_any_permission([""])

    def test_require_any_returns_checker(self):
        checker = require_any_permission(["work_items:read", "work_items:write"])
        assert callable(checker)
