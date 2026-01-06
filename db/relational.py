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

# 定义全局异步会话工厂
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
    - 支持从 configs/ 目录下的所有 .json 文件加载
    - 支持事项类型、流程状态及流转地图的自动同步与校验
    """
    log.info("开始从配置文件初始化基础数据...")

    config_dir = os.path.join(os.path.dirname(__file__), "..", "configs")
    if not os.path.exists(config_dir):
        log.warning(f"配置目录不存在: {config_dir}")
        return

    work_types_map = {}
    states_map = {}
    workflow_configs_map = {}

    # 1. 加载所有 JSON 配置文件
    for filename in os.listdir(config_dir):
        if not filename.endswith(".json"):
            continue
            
        try:
            with open(os.path.join(config_dir, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # 收集事项类型
                for item in data.get("work_types", []):
                    if isinstance(item, list) and len(item) == 2:
                        work_types_map[item[0]] = item[1]
                
                # 收集流程状态
                for item in data.get("states", []):
                    if isinstance(item, list) and len(item) == 2:
                        states_map[item[0]] = item[1]
                
                # 收集流程流转配置
                wf_configs = data.get("workflow_configs", [])
                if isinstance(wf_configs, dict):
                    for type_code, configs in wf_configs.items():
                        if type_code not in workflow_configs_map:
                            workflow_configs_map[type_code] = []
                        workflow_configs_map[type_code].extend(configs)
                else:
                    for cfg in wf_configs:
                        type_code = cfg.get("type_code")
                        if type_code:
                            if type_code not in workflow_configs_map:
                                workflow_configs_map[type_code] = []
                            workflow_configs_map[type_code].append(cfg)
        except Exception as e:
            log.error(f"解析配置文件 {filename} 失败: {e}")

    # 2. 初始化事项类型 (SysWorkType)
    for code, name in work_types_map.items():
        obj = await session.get(SysWorkType, code)
        if obj:
            obj.name = name
        else:
            session.add(SysWorkType(code=code, name=name))

    # 3. 初始化流程状态 (SysWorkflowState)
    for code, name in states_map.items():
        obj = await session.get(SysWorkflowState, code)
        if obj:
            obj.name = name
        else:
            session.add(SysWorkflowState(code=code, name=name))

    # 4. 初始化流程流转配置 (SysWorkflowConfig)
    for type_code, configs in workflow_configs_map.items():
        if type_code not in work_types_map:
            log.warning(f"跳过未知的事项类型配置: {type_code}")
            continue

        for cfg in configs:
            from_state = cfg.get("from_state")
            action = cfg.get("action")
            to_state = cfg.get("to_state")

            if from_state not in states_map or to_state not in states_map:
                log.warning(f"跳过包含未知状态的流转配置: {type_code} ({from_state} -> {to_state})")
                continue

            # 检查是否已存在相同的流转配置，存在则更新，不存在则插入
            stmt = select(SysWorkflowConfig).where(
                SysWorkflowConfig.type_code == type_code,
                SysWorkflowConfig.from_state == from_state,
                SysWorkflowConfig.action == action
            )
            result = await session.execute(stmt)
            existing_cfg = result.scalar_one_or_none()

            config_data = {
                "type_code": type_code,
                "from_state": from_state,
                "action": action,
                "to_state": to_state,
                "target_owner_strategy": cfg.get("target_owner_strategy", "KEEP"),
                "required_fields": cfg.get("required_fields", []),
                "properties": cfg.get("properties", {})
            }

            if existing_cfg:
                # 更新现有配置
                for key, value in config_data.items():
                    setattr(existing_cfg, key, value)
            else:
                # 插入新配置
                session.add(SysWorkflowConfig(**config_data))

    await session.commit()
    log.success("基础数据同步完成")
