#!/usr/bin/env python3
"""
MongoDB 数据库初始化脚本

功能说明：
该脚本用于将代码中的配置（configs/*.json）同步到 MongoDB 数据库。
RBAC 权限与角色初始化由 scripts/init/init_rbac.py 独立管理。
它是幂等的（Idempotent），可以重复运行。

用法：
  python app/init_mongodb.py              # 同步 workflow 配置 + 导航定义
  python scripts/init/init_rbac.py        # 同步 RBAC 权限与角色
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pymongo import AsyncMongoClient
from beanie import init_beanie

from app.shared.config import get_settings
from app.shared.core.logger import log
from app.modules.workflow.repository.models import (
    SysWorkTypeDoc,
    SysWorkflowStateDoc,
    SysWorkflowConfigDoc,
)
from app.modules.auth.repository.models import NavigationPageDoc
from app.modules.auth.service.navigation_page_service import DEFAULT_NAVIGATION_PAGES


def _parse_state_entry(entry: Any) -> Optional[tuple[str, str, Optional[bool]]]:
    """解析状态配置（dict 格式）。"""
    if not isinstance(entry, dict):
        return None
    code = str(entry.get("code", "")).strip()
    name = str(entry.get("name", "")).strip()
    if not code or not name:
        return None
    raw_is_end = entry.get("is_end")
    is_end = bool(raw_is_end) if raw_is_end is not None else None
    return code, name, is_end


def _merge_work_types(data: Dict[str, Any], work_types_map: Dict[str, str]) -> None:
    """合并事项类型配置。"""
    for item in data.get("work_types", []):
        if isinstance(item, list) and len(item) == 2:
            work_types_map[item[0]] = item[1]


def _merge_states(data: Dict[str, Any], states_map: Dict[str, Dict[str, Any]]) -> None:
    """合并状态定义并校验冲突。"""
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
            continue

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


def _merge_workflow_configs(
    data: Dict[str, Any],
    workflow_configs_map: Dict[str, list[dict]],
) -> None:
    """合并工作流配置（按 type_code 组织）。"""
    wf_configs = data.get("workflow_configs", {})
    if isinstance(wf_configs, dict):
        for type_code, configs in wf_configs.items():
            workflow_configs_map.setdefault(type_code, []).extend(configs)


def _load_config_maps(
    config_dir: Path,
) -> tuple[Dict[str, str], Dict[str, Dict[str, Any]], Dict[str, list[dict]]]:
    """从配置目录加载并合并所有配置。"""
    work_types_map: Dict[str, str] = {}
    states_map: Dict[str, Dict[str, Any]] = {}
    workflow_configs_map: Dict[str, list[dict]] = {}

    for filename in os.listdir(config_dir):
        if not filename.endswith(".json"):
            continue

        try:
            with open(config_dir / filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log.error(f"解析配置文件 {filename} 失败: {e}")
            raise

        _merge_work_types(data, work_types_map)
        _merge_states(data, states_map)
        _merge_workflow_configs(data, workflow_configs_map)

    return work_types_map, states_map, workflow_configs_map


def _validate_workflow_configs(
    work_types_map: Dict[str, str],
    states_map: Dict[str, Dict[str, Any]],
    workflow_configs_map: Dict[str, list[dict]],
) -> set[str]:
    """校验工作流配置并返回所有存在出边的状态。"""
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

    return from_states


def _derive_state_end_flags(states_map: Dict[str, Dict[str, Any]], from_states: set[str]) -> None:
    """推导状态是否为终态。"""
    for state_code, meta in states_map.items():
        explicit_is_end = meta.get("is_end_explicit")
        meta["is_end"] = explicit_is_end if explicit_is_end is not None else state_code not in from_states


async def _upsert_doc(Model, filter_expr, set_data, insert_data) -> None:
    """通用 upsert 辅助函数。"""
    now = datetime.now(timezone.utc)
    await Model.find_one(filter_expr).upsert(
        {"$set": {**set_data, "updated_at": now}},
        on_insert=insert_data
    )


async def _sync_work_types(work_types_map: Dict[str, str]) -> None:
    """同步事项类型。"""
    for code, name in work_types_map.items():
        await _upsert_doc(
            SysWorkTypeDoc, SysWorkTypeDoc.code == code,
            {"name": name},
            SysWorkTypeDoc(code=code, name=name)
        )
        log.info(f"初始化事项类型: {code}")


async def _sync_workflow_states(states_map: Dict[str, Dict[str, Any]]) -> None:
    """同步状态定义。"""
    for code, meta in states_map.items():
        name = meta["name"]
        is_end = bool(meta["is_end"])
        await _upsert_doc(
            SysWorkflowStateDoc, SysWorkflowStateDoc.code == code,
            {"name": name, "is_end": is_end},
            SysWorkflowStateDoc(code=code, name=name, is_end=is_end)
        )
        log.info(f"初始化流程状态: {code}")


async def _sync_workflow_configs(
    work_types_map: Dict[str, str],
    workflow_configs_map: Dict[str, list[dict]],
) -> None:
    """同步流转配置。"""
    for type_code, configs in workflow_configs_map.items():
        if type_code not in work_types_map:
            continue  # 跳过未定义类型的工作流

        for cfg in configs:
            await _upsert_doc(
                SysWorkflowConfigDoc,
                (SysWorkflowConfigDoc.type_code == type_code)
                & (SysWorkflowConfigDoc.from_state == cfg.get("from_state"))
                & (SysWorkflowConfigDoc.action == cfg.get("action")),
                {
                    "to_state": cfg.get("to_state"),
                    "target_owner_strategy": cfg.get("target_owner_strategy", "KEEP"),
                    "required_fields": cfg.get("required_fields", []),
                    "properties": cfg.get("properties", {}),
                },
                SysWorkflowConfigDoc(type_code=type_code, **cfg)
            )
            log.info(
                f"初始化流转配置: {type_code} {cfg.get('from_state')} -> {cfg.get('action')}"
            )


async def _cleanup_removed(
    Model,
    desired_keys: set,
    key_attrs: str | tuple[str, ...],
    label: str,
) -> None:
    """删除数据库中不再存在于配置中的记录。"""
    existing = await Model.find_all().to_list()
    for doc in existing:
        key = getattr(doc, key_attrs) if isinstance(key_attrs, str) else tuple(getattr(doc, a) for a in key_attrs)
        if key not in desired_keys:
            await doc.delete()
            log.info(f"删除已下线{label}: {key}")


async def _cleanup_removed_work_types(work_types_map: Dict[str, str]) -> None:
    """删除配置中已移除的事项类型。"""
    await _cleanup_removed(SysWorkTypeDoc, set(work_types_map.keys()), "code", "事项类型")


async def _cleanup_removed_workflow_configs(
    work_types_map: Dict[str, str],
    workflow_configs_map: Dict[str, list[dict]],
) -> None:
    """删除配置中已移除的流转配置。"""
    desired_keys = {
        (type_code, cfg.get("from_state"), cfg.get("action"))
        for type_code, configs in workflow_configs_map.items()
        if type_code in work_types_map
        for cfg in configs
    }
    await _cleanup_removed(
        SysWorkflowConfigDoc, desired_keys,
        ("type_code", "from_state", "action"),
        "流转配置",
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

    work_types_map, states_map, workflow_configs_map = _load_config_maps(config_dir)

    if not states_map:
        raise ValueError("未加载到任何状态定义，请在配置文件中声明 states")

    from_states = _validate_workflow_configs(work_types_map, states_map, workflow_configs_map)
    _derive_state_end_flags(states_map, from_states)

    await _sync_work_types(work_types_map)
    await _sync_workflow_states(states_map)
    await _sync_workflow_configs(work_types_map, workflow_configs_map)
    await _cleanup_removed_work_types(work_types_map)
    await _cleanup_removed_workflow_configs(work_types_map, workflow_configs_map)

    log.success("基础数据初始化完成")


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
    主函数

    功能：
    1. 连接 MongoDB。
    2. 初始化 Beanie ODM。
    3. 同步 workflow 配置 + 导航页面定义。
    4. 优雅关闭连接。

    注意：RBAC 初始化由 scripts/init/init_rbac.py 独立完成。
    """
    log.info("开始 MongoDB 初始化...")

    client = AsyncMongoClient(get_settings().mongodb.uri)

    try:
        # 测试连接
        await client.admin.command('ping')
        log.success("MongoDB 连接成功")

        # 初始化 Beanie，注册模型
        await init_beanie(
            database=client[get_settings().mongodb.db_name],
            document_models=[
                SysWorkTypeDoc,
                SysWorkflowStateDoc,
                SysWorkflowConfigDoc,
                NavigationPageDoc,
            ]
        )
        log.success("Beanie 初始化完成")

        # 执行核心同步逻辑
        await init_config_data()
        await init_navigation_pages()

        log.success("MongoDB 初始化完成!")
    except Exception as e:
        log.error(f"MongoDB 初始化失败: {e}")
        raise
    finally:
        await client.close()
        log.info("MongoDB 连接已关闭")


if __name__ == "__main__":
    asyncio.run(main())
