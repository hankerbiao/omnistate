"""MongoDB 原子序列号服务。"""
from datetime import datetime, timezone
from typing import Optional

from pymongo import AsyncMongoClient, ReturnDocument

from app.shared.core.mongo_client import get_mongo_client
from app.shared.db.config import settings


class SequenceIdService:
    """基于 Mongo find_one_and_update 的原子序列服务。"""

    COUNTERS_COLLECTION = "sys_counters"

    def __init__(self, client: Optional[AsyncMongoClient] = None):
        self._client = client

    async def next(self, key: str, session=None) -> int:
        """获取指定 key 的下一个序号（从 1 开始）。"""
        client = self._client or get_mongo_client()
        collection = client[settings.MONGO_DB_NAME][self.COUNTERS_COLLECTION]
        now = datetime.now(timezone.utc)
        doc = await collection.find_one_and_update(
            {"_id": key},
            {
                "$inc": {"seq": 1},
                "$set": {"updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        return int(doc["seq"])

