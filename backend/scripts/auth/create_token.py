#!/usr/bin/env python3
"""创建 JWT Token 脚本。

用法示例：
python scripts/create_token.py \
  --user-id admin \
  --expire-minutes 480

说明：
- 需要指定有效的 user_id，会先从数据库校验用户是否存在且状态为 ACTIVE
- 默认 token 有效期为 480 分钟（8小时），可通过 --expire-minutes 自定义
- 生成的 token 可用于 API 访问的 Authorization 头：Bearer <token>
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from beanie import init_beanie
from pymongo import AsyncMongoClient

# 允许从 scripts 目录直接运行
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.db.config import settings
from app.shared.auth.jwt_auth import create_access_token
from app.modules.auth.repository.models import UserDoc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="创建 JWT Token")
    parser.add_argument(
        "--user-id",
        required=True,
        help="用户唯一 ID（将从数据库校验用户存在性和状态）"
    )
    parser.add_argument(
        "--expire-minutes",
        type=int,
        default=480,
        help="Token 有效期（分钟），默认 480 分钟（8小时）"
    )
    parser.add_argument(
        "--save-to-file",
        type=str,
        metavar="FILE",
        help="将生成的 token 保存到指定文件（可选）"
    )
    parser.add_argument(
        "--print-payload",
        action="store_true",
        help="同时打印 token 的 payload 内容（JSON 格式）"
    )
    return parser.parse_args()


async def validate_user(user_id: str) -> bool:
    """校验用户是否存在且处于 ACTIVE 状态。"""
    user = await UserDoc.find_one(UserDoc.user_id == user_id)
    if not user:
        print(f"❌ 用户不存在: {user_id}")
        return False

    if user.status != "ACTIVE":
        print(f"❌ 用户状态非 ACTIVE: {user_id} (当前状态: {user.status})")
        return False

    print(f"✓ 用户校验通过: {user_id} ({user.username})")
    return True


async def main() -> None:
    args = parse_args()

    # 连接 MongoDB 并初始化 Beanie
    client = AsyncMongoClient(settings.MONGO_URI)
    try:
        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[UserDoc],
        )

        # 校验用户存在性
        if not await validate_user(args.user_id):
            sys.exit(1)

        # 生成 token
        print(f"\n正在生成 token...")
        print(f"  用户ID: {args.user_id}")
        print(f"  有效期: {args.expire_minutes} 分钟")

        token = create_access_token(
            subject=args.user_id,
            expires_minutes=args.expire_minutes
        )

        print(f"\n{'=' * 80}")
        print(f"Token 生成成功:")
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
                # 解析 token 的 payload 部分（不验证签名）
                import base64
                import json
                import time

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

        print("\n使用说明:")
        print("  1. 在 API 请求中，将 token 放在 Authorization 头中")
        print(f"     Authorization: Bearer {token[:20]}...")
        print("  2. 注意 token 的过期时间，过期后需要重新生成")
        print()

    finally:
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


if __name__ == "__main__":
    asyncio.run(main())