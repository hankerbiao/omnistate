import json
import os
from models import (
    SysWorkflowConfig, SysWorkType, SysWorkflowState, SQLModel,
    select
)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings
from core.logger import log
from typing import AsyncGenerator

# 异步引擎 - 必须使用 create_async_engine
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

# 定义全局异步会话工厂 (问题 4 修复)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    提供数据库会话的异步生成器
    - 供 FastAPI 依赖注入使用
    - 使用全局 AsyncSessionLocal 工厂
    """
    async with AsyncSessionLocal() as session:
        yield session


# 类型别名
AsyncSessionDep = AsyncGenerator[AsyncSession, None]


async def init_db():
    """
    初始化数据库表结构 (DDL)
    - 遍历 SQLModel 注册的所有模型并在数据库中创建对应的表
    """
    log.info("开始初始化数据库表结构...")
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    log.success("数据库表结构初始化完成")


async def init_mock_config(session: AsyncSession):
    """
    初始化基础配置数据 (Seeding)
    - 从 configs/workflow_initial_data.json 加载事项类型、流程状态及流转地图
    """
    log.info("开始从配置文件初始化基础数据...")

    # 构建配置文件的绝对路径
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "workflow_initial_data.json")
    if not os.path.exists(config_path):
        log.warning(f"配置文件不存在，跳过基础数据初始化: {config_path}")
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log.error(f"解析配置文件失败: {e}")
        return

    # 1. 初始化事项类型 (SysWorkType)
    for code, name in data.get("work_types", []):
        result = await session.get(SysWorkType, code)
        if result is None:
            session.add(SysWorkType(code=code, name=name))

    # 2. 初始化流程状态 (SysWorkflowState)
    for code, name in data.get("states", []):
        result = await session.get(SysWorkflowState, code)
        if result is None:
            session.add(SysWorkflowState(code=code, name=name))

    # 3. 初始化流程流转配置 (SysWorkflowConfig)
    for cfg in data.get("workflow_configs", []):
        # 检查是否已存在相同的流转配置，避免重复插入
        stmt = select(SysWorkflowConfig).where(
            SysWorkflowConfig.type_code == cfg["type_code"],
            SysWorkflowConfig.from_state == cfg["from_state"],
            SysWorkflowConfig.action == cfg["action"]
        )
        result = await session.execute(stmt)
        if result.first() is None:
            session.add(SysWorkflowConfig(
                type_code=cfg["type_code"],
                from_state=cfg["from_state"],
                action=cfg["action"],
                to_state=cfg["to_state"],
                target_owner_strategy=cfg.get("target_owner_strategy", "KEEP"),
                required_fields=cfg.get("required_fields", [])
            ))

    await session.commit()
    log.success("基础数据初始化完成")
