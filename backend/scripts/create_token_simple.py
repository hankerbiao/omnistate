#!/usr/bin/env python3
"""简单版 JWT Token 生成脚本（无需数据库连接）。

用法示例：
python scripts/create_token_simple.py \
  --user-id admin \
  --expire-minutes 480

说明：
- 直接生成 JWT Token，无需连接 MongoDB 或验证用户存在性
- 适用于：CI/CD 集成、自动化测试、临时token生成等场景
- 生成的 token 可用于 API 访问的 Authorization 头：Bearer <token>
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 允许从 scripts 目录直接运行
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.db.config import settings


def _b64url_encode(data: bytes) -> str:
    """Base64URL 编码"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _sign_hs256(message: bytes, secret: str) -> str:
    """使用 HS256 算法签名"""
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _b64url_encode(signature)


def create_access_token(subject: str, expires_minutes: int) -> str:
    """创建 JWT Token

    Args:
        subject: 用户ID
        expires_minutes: 有效期（分钟）

    Returns:
        JWT Token 字符串
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)

    # JWT Header
    header = {"alg": "HS256", "typ": "JWT"}

    # JWT Payload
    payload = {
        "sub": subject,                          # 主题（用户ID）
        "iat": int(now.timestamp()),             # 签发时间
        "exp": int(expire.timestamp()),          # 过期时间
        "iss": settings.JWT_ISSUER,              # 签发者
        "aud": settings.JWT_AUDIENCE,            # 接收者
    }

    # 编码 Header 和 Payload
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    # 生成签名
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature_b64 = _sign_hs256(signing_input, settings.JWT_SECRET_KEY)

    # 组装 JWT
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="生成 JWT Token（简单版，无需数据库）",
        epilog="示例: python create_token_simple.py --user-id admin --expire-minutes 480"
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="用户唯一 ID"
    )
    parser.add_argument(
        "--expire-minutes",
        type=int,
        default=480,
        help="Token 有效期（分钟），默认 480 分钟（8小时）"
    )
    parser.add_argument(
        "--secret-key",
        type=str,
        help="JWT 密钥（可选，默认使用配置文件中的设置）"
    )
    parser.add_argument(
        "--save-to-file",
        type=str,
        metavar="FILE",
        help="将生成的 token 保存到指定文件"
    )
    parser.add_argument(
        "--print-payload",
        action="store_true",
        help="同时打印 token 的 payload 内容（JSON 格式）"
    )
    return parser.parse_args()


def print_token(token: str, args: argparse.Namespace) -> None:
    """打印生成的 token"""
    print(f"\n{'=' * 80}")
    print(f"JWT Token 生成成功")
    print(f"{'=' * 80}")
    print(token)
    print(f"{'=' * 80}")

    # 如果指定了保存文件，则写入文件
    if args.save_to_file:
        try:
            with open(args.save_to_file, "w", encoding="utf-8") as f:
                f.write(token)
            print(f"\n✓ Token 已保存到文件: {args.save_to_file}")
        except Exception as e:
            print(f"\n⚠️  保存文件失败: {e}")

    # 如果需要打印 payload，则解码并打印
    if args.print_payload:
        print("\n" + "=" * 80)
        print("Token Payload 内容:")
        print("=" * 80)
        try:
            # 提取 payload 部分（第二段）
            payload_b64 = token.split(".")[1]

            # 添加 padding（如果需要）
            padding = "=" * (-len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
            payload = json.loads(payload_bytes)

            # 格式化打印
            print(json.dumps(payload, indent=2, ensure_ascii=False))

            # 计算过期时间
            exp_ts = payload.get("exp")
            if exp_ts:
                exp_time = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(exp_ts))
                now_time = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
                print(f"\n生效时间: {now_time}")
                print(f"过期时间: {exp_time}")

        except Exception as e:
            print(f"解码 payload 失败: {e}")
        finally:
            print("=" * 80)


def main() -> None:
    args = parse_args()

    # 如果提供了自定义密钥，则临时覆盖配置
    original_secret = settings.JWT_SECRET_KEY
    if args.secret_key:
        settings.JWT_SECRET_KEY = args.secret_key
        print(f"⚠️  使用自定义密钥: {args.secret_key[:10]}...")
    else:
        print(f"✓ 使用配置密钥: {settings.JWT_SECRET_KEY[:10]}...")

    try:
        # 生成 token
        print(f"\n正在生成 token...")
        print(f"  用户ID: {args.user_id}")
        print(f"  有效期: {args.expire_minutes} 分钟")

        token = create_access_token(
            subject=args.user_id,
            expires_minutes=args.expire_minutes
        )

        # 打印结果
        print_token(token, args)

        print("\n使用说明:")
        print("  1. 在 API 请求中，将 token 放在 Authorization 头中")
        print(f"     Authorization: Bearer {token[:20]}...")
        print("  2. 注意 token 的过期时间，过期后需要重新生成")
        print()

    finally:
        # 恢复原始密钥
        if args.secret_key:
            settings.JWT_SECRET_KEY = original_secret


if __name__ == "__main__":
    main()