"""
全局 MongoDB 客户端管理

用于在 Beanie ODM 中提供事务支持或执行底层 Mongo 操作。
"""
from pymongo import AsyncMongoClient

_mongo_client: AsyncMongoClient | None = None


def set_mongo_client(client: AsyncMongoClient) -> None:
    # 在应用启动阶段由 main.py 调用，将 AsyncMongoClient 存入全局变量
    global _mongo_client
    _mongo_client = client


def get_mongo_client() -> AsyncMongoClient:
    # 获取全局 Mongo 客户端：
    # - 适用于需要直接使用 PyMongo 原生 API 的场景
    # - Beanie 的常规文档操作无需依赖本方法
    global _mongo_client
    if _mongo_client is None:
        raise RuntimeError("MongoDB 客户端未初始化，请确保应用已启动")
    return _mongo_client
