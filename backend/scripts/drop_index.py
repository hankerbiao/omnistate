"""删除 automation_test_cases 集合的 linked_manual_case_id_1 索引。

用法:
    cd backend && python scripts/drop_index.py
"""
import asyncio
import os
import sys

# 确保能找到 app 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from app.shared.config import get_settings


async def main():
    settings = get_settings()
    mongo_uri = settings.mongodb.uri
    db_name = settings.mongodb.db_name

    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    collection = db["automation_test_cases"]

    # 查看当前索引
    indexes = await collection.index_information()
    print("当前索引:", list(indexes.keys()))

    # 先删除索引，否则更新数据时唯一索引冲突
    if "linked_manual_case_id_1" in indexes:
        await collection.drop_index("linked_manual_case_id_1")
        print("已删除 linked_manual_case_id_1 索引")
    else:
        print("linked_manual_case_id_1 索引不存在，跳过")

    # 将现有空字符串改为 None
    result = await collection.update_many(
        {"linked_manual_case_id": ""},
        {"$set": {"linked_manual_case_id": None}},
    )
    print(f"已清理 {result.modified_count} 条 linked_manual_case_id 为空字符串的记录")

    # 验证
    indexes = await collection.index_information()
    print("剩余索引:", list(indexes.keys()))

    client.close()
    print("完成。重启服务后 Beanie 会自动重建索引。")


asyncio.run(main())
