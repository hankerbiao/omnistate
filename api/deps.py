"""
依赖注入模块

提供 FastAPI 依赖项，包括：
- 数据库会话
- 服务实例
- 认证依赖
"""
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.relational import get_async_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    异步数据库会话依赖
    """
    async for session in get_async_session():
        yield session


# 类型别名
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]