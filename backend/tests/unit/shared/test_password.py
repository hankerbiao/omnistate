"""密码哈希与校验单元测试。"""
from __future__ import annotations

import base64

import pytest

from app.shared.auth.password import hash_password, verify_password


class TestHashPassword:
    def test_returns_valid_output(self):
        salt, hash_val = hash_password("MyP@ssw0rd!")
        # salt 和 hash 应为非空 base64 可解码字符串
        assert isinstance(salt, str)
        assert isinstance(hash_val, str)
        assert len(salt) > 0
        assert len(hash_val) > 0
        # base64 可解码
        base64.b64decode(salt)
        base64.b64decode(hash_val)

    def test_different_salt_each_call(self):
        """同一密码每次调用应产生不同的 (salt, hash) 对"""
        salt1, hash1 = hash_password("same_password")
        salt2, hash2 = hash_password("same_password")
        assert salt1 != salt2  # salt 必须不同
        assert hash1 != hash2  # hash 因 salt 不同而不同


class TestVerifyPassword:
    def test_correct_password(self):
        password = "MyP@ssw0rd!"
        salt, hash_val = hash_password(password)
        assert verify_password(password, salt, hash_val) is True

    def test_wrong_password(self):
        salt, hash_val = hash_password("correct_password")
        assert verify_password("wrong_password", salt, hash_val) is False

    def test_empty_string(self):
        """空密码的哈希和校验应正常工作"""
        salt, hash_val = hash_password("")
        assert verify_password("", salt, hash_val) is True
        assert verify_password(" ", salt, hash_val) is False

    def test_wrong_salt(self):
        _, hash_val = hash_password("password")
        other_salt, _ = hash_password("other")
        assert verify_password("password", other_salt, hash_val) is False

    def test_tampered_hash(self):
        salt, hash_val = hash_password("password")
        # 篡改 hash 的最后几个字符
        tampered = hash_val[:-3] + "abc"
        assert verify_password("password", salt, tampered) is False

    def test_unicode_password(self):
        """中文和 emoji 密码"""
        password = "密码123!@#😂"
        salt, hash_val = hash_password(password)
        assert verify_password(password, salt, hash_val) is True
        assert verify_password("密码123!@#", salt, hash_val) is False

    def test_long_password(self):
        """1000+ 字符的密码"""
        password = "a" * 2000
        salt, hash_val = hash_password(password)
        assert verify_password(password, salt, hash_val) is True
        assert verify_password("a" * 1999, salt, hash_val) is False

    def test_password_with_special_chars(self):
        """含特殊字符的密码"""
        password = "P@$$w0rd!\n\t\\x00"
        salt, hash_val = hash_password(password)
        assert verify_password(password, salt, hash_val) is True

    def test_verify_invalid_base64_salt(self):
        with pytest.raises(Exception):
            verify_password("password", "!!!invalid-base64!!!", "AAAA")

    def test_verify_invalid_base64_hash(self):
        with pytest.raises(Exception):
            verify_password("password", "AAAA", "!!!invalid-base64!!!")
