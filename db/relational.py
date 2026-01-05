import json
import os
from models import (
    SysWorkflowConfig, SysWorkType, SysWorkflowState, Session, SQLModel, 
    select
)
from sqlmodel import create_engine
from contextlib import contextmanager
from .config import settings
from core.logger import log

# 创建数据库引擎
# echo=False 关闭 SQL 日志输出，生产环境建议根据需要开启
engine = create_engine(settings.DATABASE_URL, echo=False)

@contextmanager
def get_session():
    """
    提供数据库会话的上下文管理器
    - 确保 Session 在使用后能被正确关闭
    - 典型的用法: with get_session() as session: ...
    """
    with Session(engine) as session:
        yield session

def init_db():
    """
    初始化数据库表结构 (DDL)
    - 遍历 SQLModel 注册的所有模型并在数据库中创建对应的表
    """
    log.info("开始初始化数据库表结构...")
    SQLModel.metadata.create_all(engine)
    log.success("数据库表结构初始化完成")

def init_mock_config(session: Session):
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
        if session.get(SysWorkType, code) is None:
            session.add(SysWorkType(code=code, name=name))

    # 2. 初始化流程状态 (SysWorkflowState)
    for code, name in data.get("states", []):
        if session.get(SysWorkflowState, code) is None:
            session.add(SysWorkflowState(code=code, name=name))

    # 3. 初始化流程流转配置 (SysWorkflowConfig)
    for cfg in data.get("workflow_configs", []):
        # 检查是否已存在相同的流转配置，避免重复插入
        stmt = select(SysWorkflowConfig).where(
            SysWorkflowConfig.type_code == cfg["type_code"],
            SysWorkflowConfig.from_state == cfg["from_state"],
            SysWorkflowConfig.action == cfg["action"],
        )
        if session.exec(stmt).first() is None:
            log.debug(f"添加流程配置: {cfg['type_code']} | {cfg['from_state']} --({cfg['action']})--> {cfg['to_state']}")
            session.add(SysWorkflowConfig(**cfg))
    
    session.commit()
    log.success("基础配置数据初始化完成")
