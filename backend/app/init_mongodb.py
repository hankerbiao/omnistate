#!/usr/bin/env python3
"""
MongoDB 数据库初始化脚本

功能：
1. 创建集合和索引
2. 从 configs/ 目录加载初始配置数据
"""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from pymongo import AsyncMongoClient
from beanie import init_beanie

from app.db.config import settings
from app.core.logger import log
from app.models import (
    SysWorkTypeDoc, SysWorkflowStateDoc, SysWorkflowConfigDoc,
)


async def init_config_data():
    """从配置文件初始化基础数据 (Beanie ODM 版本)"""
    log.info("开始从配置文件初始化基础数据...")

    config_dir = Path(__file__).parent / "configs"
    if not config_dir.exists():
        log.warning(f"配置目录不存在: {config_dir}")
        return

    work_types_map = {}
    # 预定义的状态映射
    states_map = {
        "DRAFT": "草稿",
        "DONE": "已完成",
        "REJECTED": "已拒绝",
        "PENDING_AUDIT": "待审核",
        "ASSIGNED": "已指派",
        "DEVELOPING": "开发中",
        "PENDING_REVIEW": "待审核"
    }
    workflow_configs_map = {}

    # 1. 加载所有 JSON 配置文件
    for filename in os.listdir(config_dir):
        if not filename.endswith(".json"):
            continue

        try:
            with open(config_dir / filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("work_types", []):
                    if isinstance(item, list) and len(item) == 2:
                        work_types_map[item[0]] = item[1]

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

    # 2. 初始化事项类型
    for code, name in work_types_map.items():
        await SysWorkTypeDoc.find_one(SysWorkTypeDoc.code == code).upsert(
            {"$set": {"name": name, "updated_at": datetime.utcnow()}},
            on_insert=SysWorkTypeDoc(code=code, name=name)
        )
        log.info(f"初始化事项类型: {code}")

    # 3. 初始化流程状态
    for code, name in states_map.items():
        is_end = code in ["DONE", "REJECTED"]
        await SysWorkflowStateDoc.find_one(SysWorkflowStateDoc.code == code).upsert(
            {"$set": {"name": name, "is_end": is_end, "updated_at": datetime.utcnow()}},
            on_insert=SysWorkflowStateDoc(code=code, name=name, is_end=is_end)
        )
        log.info(f"初始化流程状态: {code}")

    # 4. 初始化流程流转配置
    for type_code, configs in workflow_configs_map.items():
        if type_code not in work_types_map:
            continue
        for cfg in configs:
            await SysWorkflowConfigDoc.find_one(
                SysWorkflowConfigDoc.type_code == type_code,
                SysWorkflowConfigDoc.from_state == cfg.get("from_state"),
                SysWorkflowConfigDoc.action == cfg.get("action")
            ).upsert(
                {"$set": {
                    "to_state": cfg.get("to_state"),
                    "target_owner_strategy": cfg.get("target_owner_strategy", "KEEP"),
                    "required_fields": cfg.get("required_fields", []),
                    "properties": cfg.get("properties", {}),
                    "updated_at": datetime.utcnow()
                }},
                on_insert=SysWorkflowConfigDoc(**cfg)
            )
            log.info(f"初始化流转配置: {type_code} {cfg.get('from_state')} -> {cfg.get('action')}")

    log.success("基础数据初始化完成")


async def main():
    """主函数 (Beanie ODM 版本)"""
    log.info("开始 MongoDB 初始化...")

    client = AsyncMongoClient(settings.MONGO_URI)

    try:
        await client.admin.command('ping')
        log.success("MongoDB 连接成功")

        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[
                SysWorkTypeDoc,
                SysWorkflowStateDoc,
                SysWorkflowConfigDoc
            ]
        )
        log.success("Beanie 初始化完成")

        await init_config_data()

        log.success("MongoDB 初始化完成!")
    except Exception as e:
        log.error(f"MongoDB 初始化失败: {e}")
        raise
    finally:
        client.close()
        log.info("MongoDB 连接已关闭")


if __name__ == "__main__":
    asyncio.run(main())
