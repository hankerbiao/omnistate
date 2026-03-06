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
from typing import Any, Dict, Optional

from pymongo import AsyncMongoClient
from beanie import init_beanie

from app.shared.db.config import settings
from app.shared.core.logger import log
from app.modules.workflow.repository.models import (
    SysWorkTypeDoc,
    SysWorkflowStateDoc,
    SysWorkflowConfigDoc,
)
from app.modules.auth.repository.models import (
    PermissionDoc,
    RoleDoc,
    NavigationPageDoc,
)
from app.modules.auth.service.navigation_page_service import DEFAULT_NAVIGATION_PAGES


def _parse_state_entry(entry: Any) -> Optional[tuple[str, str, Optional[bool]]]:
    """兼容多种 states 配置格式并标准化。"""
    if isinstance(entry, list):
        if len(entry) < 2:
            return None
        code = str(entry[0]).strip()
        name = str(entry[1]).strip()
        is_end = bool(entry[2]) if len(entry) >= 3 else None
        return code, name, is_end

    if isinstance(entry, dict):
        code = str(entry.get("code", "")).strip()
        name = str(entry.get("name", "")).strip()
        if not code or not name:
            return None
        raw_is_end = entry.get("is_end")
        is_end = bool(raw_is_end) if raw_is_end is not None else None
        return code, name, is_end

    return None


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
    work_types_map: Dict[str, str] = {}
    # 状态定义：code -> {"name": str, "is_end_explicit": Optional[bool], "is_end": bool}
    states_map: Dict[str, Dict[str, Any]] = {}
    # 存储流转配置： type_code -> [config_dict, ...]
    workflow_configs_map: Dict[str, list[dict]] = {}

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

                # 解析状态定义 (states)
                for state_entry in data.get("states", []):
                    parsed = _parse_state_entry(state_entry)
                    if parsed is None:
                        raise ValueError(f"非法 states 配置项: {state_entry}")
                    state_code, state_name, state_is_end = parsed

                    existing_state = states_map.get(state_code)
                    if existing_state is None:
                        states_map[state_code] = {
                            "name": state_name,
                            "is_end_explicit": state_is_end,
                        }
                    else:
                        if existing_state["name"] != state_name:
                            raise ValueError(
                                f"状态定义冲突: code={state_code}, "
                                f"name='{existing_state['name']}' vs '{state_name}'"
                            )
                        if state_is_end is not None:
                            explicit = existing_state.get("is_end_explicit")
                            if explicit is not None and explicit != state_is_end:
                                raise ValueError(f"状态 is_end 定义冲突: code={state_code}")
                            existing_state["is_end_explicit"] = state_is_end

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
            raise

    if not states_map:
        raise ValueError("未加载到任何状态定义，请在配置文件中声明 states")

    # --- 2.1 一致性校验（工作流配置引用） ---
    validation_errors: list[str] = []
    seen_transitions: set[tuple[str, str, str]] = set()
    from_states: set[str] = set()

    for type_code, configs in workflow_configs_map.items():
        if type_code not in work_types_map:
            validation_errors.append(f"workflow_configs 引用了未定义的 type_code: {type_code}")
            continue

        for cfg in configs:
            from_state = cfg.get("from_state")
            to_state = cfg.get("to_state")
            action = cfg.get("action")

            if not from_state or not to_state or not action:
                validation_errors.append(
                    f"{type_code} 存在缺失字段的流转配置: "
                    f"from_state={from_state}, action={action}, to_state={to_state}"
                )
                continue

            if from_state not in states_map:
                validation_errors.append(
                    f"{type_code}/{action} 引用了未定义 from_state: {from_state}"
                )
            if to_state not in states_map:
                validation_errors.append(
                    f"{type_code}/{action} 引用了未定义 to_state: {to_state}"
                )

            transition_key = (type_code, from_state, action)
            if transition_key in seen_transitions:
                validation_errors.append(
                    f"重复流转配置: type={type_code}, from={from_state}, action={action}"
                )
            seen_transitions.add(transition_key)
            from_states.add(from_state)

    if validation_errors:
        raise ValueError("配置一致性校验失败: " + " | ".join(validation_errors))

    # 推导终态：显式配置优先，否则使用“无出边状态即终态”
    for state_code, meta in states_map.items():
        explicit_is_end = meta.get("is_end_explicit")
        meta["is_end"] = explicit_is_end if explicit_is_end is not None else state_code not in from_states

    # --- 3. 初始化事项类型 (SysWorkTypeDoc) ---
    for code, name in work_types_map.items():
        # upsert: 存在则更新 $set 指定的字段，不存在则插入 on_insert
        await SysWorkTypeDoc.find_one(SysWorkTypeDoc.code == code).upsert(
            {"$set": {"name": name, "updated_at": datetime.now(timezone.utc)}},
            on_insert=SysWorkTypeDoc(code=code, name=name)
        )
        log.info(f"初始化事项类型: {code}")

    # --- 4. 初始化流程状态 (SysWorkflowStateDoc) ---
    for code, meta in states_map.items():
        name = meta["name"]
        is_end = bool(meta["is_end"])
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


async def init_rbac_data():
    """
    初始化 RBAC 默认权限与 ADMIN 角色。

    说明：
    - 权限以 perm_id/code 统一为权限码（如 work_items:read）
    - ADMIN 角色默认拥有全部权限
    """
    log.info("开始初始化 RBAC 权限与角色...")

    default_permissions = [
        # workflow
        ("work_items:read", "工作流读取权限"),
        ("work_items:write", "工作流写入权限"),
        ("work_items:transition", "工作流流转权限"),
        # rbac
        ("users:read", "用户读取权限"),
        ("users:write", "用户写入权限"),
        ("roles:read", "角色读取权限"),
        ("roles:write", "角色写入权限"),
        ("permissions:read", "权限读取权限"),
        ("permissions:write", "权限写入权限"),
        # assets (预留)
        ("assets:read", "资产读取权限"),
        ("assets:write", "资产写入权限"),
        # test specs (预留)
        ("requirements:read", "需求读取权限"),
        ("requirements:write", "需求写入权限"),
        ("test_cases:read", "用例读取权限"),
        ("test_cases:write", "用例写入权限"),
        ("execution_tasks:read", "执行任务读取权限"),
        ("execution_tasks:write", "执行任务写入权限"),
        ("navigation:read", "导航读取权限"),
        ("navigation:write", "导航写入权限"),
    ]

    # 1) upsert 权限
    for code, name in default_permissions:
        await PermissionDoc.find_one(PermissionDoc.perm_id == code).upsert(
            {"$set": {"code": code, "name": name, "updated_at": datetime.now(timezone.utc)}},
            on_insert=PermissionDoc(perm_id=code, code=code, name=name)
        )

    # 2) upsert 默认角色
    all_perm_ids = [code for code, _ in default_permissions]
    default_roles = {
        "ADMIN": all_perm_ids,
        "TPM": [
            "users:read",
            "requirements:read",
            "requirements:write",
            "test_cases:read",
            "assets:read",
            "assets:write",
            "work_items:read",
            "work_items:transition",
            "execution_tasks:read",
            "execution_tasks:write",
            "navigation:read",
            "navigation:write",
        ],
        "TESTER": [
            "users:read",
            "requirements:read",
            "test_cases:read",
            "test_cases:write",
            "assets:read",
            "assets:write",
            "work_items:read",
            "work_items:transition",
            "execution_tasks:read",
            "navigation:read",
            "navigation:write",
        ],
        "AUTOMATION": [
            "users:read",
            "test_cases:read",
            "test_cases:write",
            "assets:read",
            "work_items:read",
            "execution_tasks:read",
            "navigation:read",
            "navigation:write",
        ],
    }

    for role_id, permission_ids in default_roles.items():
        await RoleDoc.find_one(RoleDoc.role_id == role_id).upsert(
            {"$set": {"name": role_id, "permission_ids": permission_ids, "updated_at": datetime.now(timezone.utc)}},
            on_insert=RoleDoc(role_id=role_id, name=role_id, permission_ids=permission_ids)
        )

    log.success("RBAC 初始化完成")


async def init_navigation_pages():
    """初始化默认导航页面定义。"""
    log.info("开始初始化导航页面定义...")

    for item in DEFAULT_NAVIGATION_PAGES:
        view = item["view"]
        await NavigationPageDoc.find_one(NavigationPageDoc.view == view).upsert(
            {
                "$set": {
                    "label": item["label"],
                    "permission": item.get("permission"),
                    "description": item.get("description"),
                    "order": item.get("order", 0),
                    "is_active": bool(item.get("is_active", True)),
                    "is_deleted": False,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            on_insert=NavigationPageDoc(
                view=view,
                label=item["label"],
                permission=item.get("permission"),
                description=item.get("description"),
                order=item.get("order", 0),
                is_active=bool(item.get("is_active", True)),
            ),
        )

    log.success("导航页面初始化完成")


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
                SysWorkflowConfigDoc,
                PermissionDoc,
                RoleDoc,
                NavigationPageDoc,
            ]
        )
        log.success("Beanie 初始化完成")

        # 执行核心同步逻辑
        await init_config_data()
        await init_rbac_data()
        await init_navigation_pages()

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
