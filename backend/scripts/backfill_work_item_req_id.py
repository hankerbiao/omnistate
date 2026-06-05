"""回填 BusWorkItemDoc.req_id 冗余字段

将已有的 REQUIREMENT 类型工作项从 TestRequirementDoc 回填 req_id，
使 serialize_work_item 无需跨集合查询。

用法:
    cd backend && python scripts/backfill_work_item_req_id.py
"""
import asyncio
import sys
from pathlib import Path

# 确保可以 import app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.modules.test_specs.repository.models import TestRequirementDoc
from app.modules.workflow.repository.models import BusWorkItemDoc
from app.shared.core.config import settings


async def main():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 只注册需要的模型，跳过索引同步
    await init_beanie(database=db, document_models=[BusWorkItemDoc, TestRequirementDoc], skip_indexes=True)

    # 查找所有 REQUIREMENT 类型且没有 req_id 的工作项
    items = await BusWorkItemDoc.find(
        BusWorkItemDoc.type_code == "REQUIREMENT",
        {"is_deleted": False, "req_id": None},
    ).to_list()

    print(f"找到 {len(items)} 个需要回填 req_id 的 REQUIREMENT 工作项")

    updated = 0
    for item in items:
        requirement = await TestRequirementDoc.find_one(
            {"workflow_item_id": str(item.id), "is_deleted": False}
        )
        if requirement and requirement.req_id:
            item.req_id = requirement.req_id
            await item.save()
            updated += 1
            print(f"  ✓ {item.id} → req_id={requirement.req_id}")
        else:
            print(f"  ⚠ {item.id} → 未找到对应的 TestRequirementDoc")

    print(f"\n完成: 回填 {updated}/{len(items)} 条")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
