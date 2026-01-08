#!/usr/bin/env python3
"""
MongoDB 数据库初始化脚本

功能说明：
该脚本用于将代码中的配置（configs/*.json）同步到 MongoDB 数据库中。
它是幂等的（Idempotent），可以重复运行。

主要逻辑：
1. **加载配置**：从 `configs/` 目录读取 JSON 配置文件，解析出事项类型、工作流状态、流转规则。
2. **数据同步 (Upsert)**：
   - 使用 `upsert` (Update + Insert) 操作。
   - 如果数据不存在，则创建。
   - 如果数据已存在，则使用 `$set` 更新指定字段（如 name, to_state），**保留**其他自定义字段。
3. **数据清理 (Cleanup)**：
   - 反向检查数据库中的数据。
   - 如果数据库中存在某条配置，但配置文件中已将其移除，脚本会**物理删除**该文档。
   - 注意：这意味着未在配置文件中定义的“野生”数据会被清除。

使用方法：
python backend/app/init_mongodb.py
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from pymongo import AsyncMongoClient
from beanie import init_beanie

from app.db.config import settings
from app.core.logger import log
from app.models import (
    SysWorkTypeDoc, SysWorkflowStateDoc, SysWorkflowConfigDoc,
)


async def init_config_data():
    """
    从配置文件初始化基础数据 (Beanie ODM 版本)
    
    流程：
    1. 扫描 `configs/` 目录，加载 JSON 配置到内存字典。
    2. 同步 `SysWorkTypeDoc` (事项类型)。
    3. 同步 `SysWorkflowStateDoc` (工作流状态)。
    4. 同步 `SysWorkflowConfigDoc` (流转规则)。
    5. 清理数据库中已废弃（配置文件中不存在）的数据。
    """
    log.info("开始从配置文件初始化基础数据...")

    config_dir = Path(__file__).parent / "configs"
    if not config_dir.exists():
        log.warning(f"配置目录不存在: {config_dir}")
        return

    # --- 1. 准备内存数据结构 ---
    
    work_types_map = {}
    
    # 预定义的状态映射 (Code -> Name)
    states_map = {
        "DRAFT": "草稿",
        "PENDING_REVIEW": "待评审",
        "PENDING_DEVELOP": "待开发",
        "DEVELOPING": "开发中",
        "PENDING_TEST": "待测试",
        "PENDING_UAT": "待验收",
        "PENDING_RELEASE": "待上线",
        "RELEASED": "已上线",
        "DONE": "已完成",
        "REJECTED": "已拒绝",
        # 兼容旧配置
        "PENDING_AUDIT": "待审核",
        "ASSIGNED": "已指派"
    }
    
    # 存储流转配置： type_code -> [config_dict, ...]
    workflow_configs_map = {}

    # --- 2. 加载 JSON 配置文件 ---
    for filename in os.listdir(config_dir):
        if not filename.endswith(".json"):
            continue

        try:
            with open(config_dir / filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # 解析事项类型 (work_types)
                for item in data.get("work_types", []):
                    if isinstance(item, list) and len(item) == 2:
                        work_types_map[item[0]] = item[1]

                # 解析流转配置 (workflow_configs)
                wf_configs = data.get("workflow_configs", [])
                if isinstance(wf_configs, dict):
                    # 格式 A: {"REQ": [...], "TASK": [...]}
                    for type_code, configs in wf_configs.items():
                        if type_code not in workflow_configs_map:
                            workflow_configs_map[type_code] = []
                        workflow_configs_map[type_code].extend(configs)
                else:
                    # 格式 B: [{"type_code": "REQ", ...}, ...]
                    for cfg in wf_configs:
                        type_code = cfg.get("type_code")
                        if type_code:
                            if type_code not in workflow_configs_map:
                                workflow_configs_map[type_code] = []
                            workflow_configs_map[type_code].append(cfg)
        except Exception as e:
            log.error(f"解析配置文件 {filename} 失败: {e}")

    # --- 3. 初始化事项类型 (SysWorkTypeDoc) ---
    for code, name in work_types_map.items():
        # upsert: 存在则更新 $set 指定的字段，不存在则插入 on_insert
        await SysWorkTypeDoc.find_one(SysWorkTypeDoc.code == code).upsert(
            {"$set": {"name": name, "updated_at": datetime.now(timezone.utc)}},
            on_insert=SysWorkTypeDoc(code=code, name=name)
        )
        log.info(f"初始化事项类型: {code}")

    # --- 4. 初始化流程状态 (SysWorkflowStateDoc) ---
    for code, name in states_map.items():
        is_end = code in ["DONE", "REJECTED", "RELEASED"]
        await SysWorkflowStateDoc.find_one(SysWorkflowStateDoc.code == code).upsert(
            {"$set": {"name": name, "is_end": is_end, "updated_at": datetime.now(timezone.utc)}},
            on_insert=SysWorkflowStateDoc(code=code, name=name, is_end=is_end)
        )
        log.info(f"初始化流程状态: {code}")

    # --- 5. 初始化流程流转配置 (SysWorkflowConfigDoc) ---
    for type_code, configs in workflow_configs_map.items():
        if type_code not in work_types_map:
            continue # 跳过未定义类型的工作流
            
        for cfg in configs:
            # 唯一键：type_code + from_state + action
            # 意味着同一个类型下，同一个状态不能有两个相同的动作
            await SysWorkflowConfigDoc.find_one(
                SysWorkflowConfigDoc.type_code == type_code,
                SysWorkflowConfigDoc.from_state == cfg.get("from_state"),
                SysWorkflowConfigDoc.action == cfg.get("action")
            ).upsert(
                {"$set": {
                    # 只更新这些字段，保留其他可能存在的扩展字段
                    "to_state": cfg.get("to_state"),
                    "target_owner_strategy": cfg.get("target_owner_strategy", "KEEP"),
                    "required_fields": cfg.get("required_fields", []),
                    "properties": cfg.get("properties", {}),
                    "updated_at": datetime.now(timezone.utc)
                }},
                on_insert=SysWorkflowConfigDoc(type_code=type_code, **cfg)
            )
            log.info(f"初始化流转配置: {type_code} {cfg.get('from_state')} -> {cfg.get('action')}")

    # --- 6. 清理逻辑：删除已下线的事项类型 ---
    # 警告：这会物理删除数据库中存在但配置文件中不存在的记录
    existing_types = await SysWorkTypeDoc.find_all().to_list()
    for doc in existing_types:
        if doc.code not in work_types_map:
            await doc.delete()
            log.info(f"删除已下线事项类型: {doc.code}")

    # --- 7. 清理逻辑：删除已下线的流转配置 ---
    # 构建当前配置中所有合法的 (type_code, from_state, action) 集合
    desired_workflow_keys = set()
    for type_code, configs in workflow_configs_map.items():
        if type_code not in work_types_map:
            continue
        for cfg in configs:
            key = (type_code, cfg.get("from_state"), cfg.get("action"))
            desired_workflow_keys.add(key)

    # 遍历数据库现有记录，如果不在合法集合中，则删除
    existing_workflows = await SysWorkflowConfigDoc.find_all().to_list()
    for cfg_doc in existing_workflows:
        key = (cfg_doc.type_code, cfg_doc.from_state, cfg_doc.action)
        if key not in desired_workflow_keys:
            await cfg_doc.delete()
            log.info(f"删除已下线流转配置: {cfg_doc.type_code} {cfg_doc.from_state} -> {cfg_doc.action}")

    log.success("基础数据初始化完成")


async def main():
    """
    主函数 (Beanie ODM 版本)
    
    功能：
    1. 连接 MongoDB。
    2. 初始化 Beanie ODM。
    3. 调用 init_config_data 执行同步。
    4. 优雅关闭连接。
    """
    log.info("开始 MongoDB 初始化...")

    client = AsyncMongoClient(settings.MONGO_URI)

    try:
        # 测试连接
        await client.admin.command('ping')
        log.success("MongoDB 连接成功")

        # 初始化 Beanie，注册模型
        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[
                SysWorkTypeDoc,
                SysWorkflowStateDoc,
                SysWorkflowConfigDoc
            ]
        )
        log.success("Beanie 初始化完成")

        # 执行核心同步逻辑
        await init_config_data()

        log.success("MongoDB 初始化完成!")
    except Exception as e:
        log.error(f"MongoDB 初始化失败: {e}")
        raise
    finally:
        # 兼容同步/异步的 close 调用
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result
        log.info("MongoDB 连接已关闭")


if __name__ == "__main__":
    asyncio.run(main())
