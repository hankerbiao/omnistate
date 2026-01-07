"""
全局 MongoDB 客户端管理

用于在 Beanie ODM 中提供事务支持的全局客户端访问。
"""
from pymongo import AsyncMongoClient

_mongo_client: AsyncMongoClient | None = None


def set_mongo_client(client: AsyncMongoClient) -> None:
    global _mongo_client
    _mongo_client = client


def get_mongo_client() -> AsyncMongoClient:
    global _mongo_client
    if _mongo_client is None:
        raise RuntimeError("MongoDB 客户端未初始化，请确保应用已启动")
    return _mongo_client
