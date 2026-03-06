#!/usr/bin/env python3
"""
演示 FastAPI 依赖执行顺序的示例

这个示例展示了一个重要的概念：
当有 `_=Depends(require_permission("navigation:write"))` 时，
必须执行完这行代码后，才会进入接口函数。
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from typing import Dict, Any
import asyncio

app = FastAPI()
security = HTTPBearer()

# 模拟用户数据库
FAKE_USERS = {
    "admin": {
        "user_id": "admin",
        "role_ids": ["ADMIN"],
        "permissions": ["navigation:write", "navigation:read"]
    },
    "user1": {
        "user_id": "user1",
        "role_ids": ["TESTER"],
        "permissions": ["navigation:read"]
    }
}

# 模拟权限验证
async def require_permission(permission_code: str):
    """权限校验依赖：要求用户拥有指定权限。"""
    print(f"🔐 开始验证权限: {permission_code}")

    def _checker(token: str = Depends(security)):
        print(f"📋 获取到 token: {token}")

        # 模拟用户查找
        user = FAKE_USERS.get(token)
        if not user:
            print("❌ 用户不存在")
            raise HTTPException(status_code=401, detail="用户不存在")

        print(f"👤 找到用户: {user['user_id']}, 角色: {user['role_ids']}")

        # 检查管理员
        if any("ADMIN" in str(role_id).upper() for role_id in user["role_ids"]):
            print("✅ 管理员用户，权限验证通过")
            return user

        # 检查权限
        if permission_code in user["permissions"]:
            print(f"✅ 用户有权限 {permission_code}，验证通过")
            return user
        else:
            print(f"❌ 用户缺少权限 {permission_code}")
            raise HTTPException(status_code=403, detail="权限不足")

    return _checker

# 依赖执行顺序演示
print("🚀 启动依赖执行顺序演示...")
print("=" * 60)

@app.post("/api/admin/pages")
async def create_page(
    request_data: Dict[str, Any],
    service_result: str = "模拟服务调用",
    permission_check=Depends(require_permission("navigation:write")),
    current_user: Dict[str, Any] = Depends(require_permission("navigation:write"))
):
    """
    这个接口演示了依赖的执行顺序：
    1. 首先执行所有的 Depends()
    2. 只有所有依赖都成功后才执行此函数
    """
    print("=" * 60)
    print("🎉 所有依赖验证完成，现在执行接口函数！")
    print(f"👤 当前用户: {current_user['user_id']}")
    print(f"📝 请求数据: {request_data}")
    print(f"🔧 服务结果: {service_result}")

    return {
        "message": "创建成功",
        "user": current_user['user_id'],
        "data": request_data
    }

# 手动模拟请求处理流程
async def simulate_request():
    """手动模拟 FastAPI 请求处理流程"""
    print("🔄 开始模拟请求处理流程...")
    print()

    # 模拟不同用户的请求
    test_cases = [
        ("admin", "应该成功"),
        ("user1", "应该被拒绝 - 权限不足")
    ]

    for token, expected in test_cases:
        print(f"📤 发送请求，用户: {token}, 期望: {expected}")
        print("-" * 40)

        try:
            # 1. 解析 token
            print("1️⃣ 步骤1: 解析 token")
            if token not in FAKE_USERS:
                raise HTTPException(401, "用户不存在")
            user = FAKE_USERS[token]
            print(f"   ✅ 用户验证成功: {user['user_id']}")

            # 2. 权限检查
            print("2️⃣ 步骤2: 权限检查")
            permission_code = "navigation:write"

            if any("ADMIN" in str(role_id).upper() for role_id in user["role_ids"]):
                print("   ✅ 管理员权限验证通过")
            elif permission_code in user["permissions"]:
                print(f"   ✅ 用户权限验证通过: {permission_code}")
            else:
                print(f"   ❌ 权限验证失败: {permission_code}")
                raise HTTPException(403, "权限不足")

            # 3. 执行接口逻辑
            print("3️⃣ 步骤3: 执行接口逻辑")
            print("   🎉 调用 create_page() 函数")
            result = {
                "message": "创建成功",
                "user": user['user_id'],
                "data": {"page_name": "测试页面"}
            }
            print(f"   ✅ 接口执行成功: {result}")

        except HTTPException as e:
            print(f"   ❌ 请求失败: {e.detail}")

        print()
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(simulate_request())