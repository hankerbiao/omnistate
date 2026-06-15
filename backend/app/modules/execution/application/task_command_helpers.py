"""执行任务命令辅助函数。

此模块提供任务命令处理所需的纯工具函数，
所有函数均为无状态静态函数，可被各服务直接调用。
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.application.constants import (
    FINAL_TASK_STATUSES,
    ConsumeStatus,
    OverallStatus,
    ScheduleStatus,
)
from app.modules.execution.repository.models import ExecutionTaskDoc
from app.modules.execution.schemas import RerunTaskRequest
from app.shared.core.datetime_utils import ensure_utc_datetime
from app.shared.core.logger import log as logger


def assign_fields(target: Any, **values: Any) -> None:
    for field_name, field_value in values.items():
        setattr(target, field_name, field_value)


def build_dedup_key(command: DispatchExecutionTaskCommand) -> str:
    """基于业务载荷构建稳定去重键。"""
    payload = {
        "dispatch_channel": command.dispatch_channel,
        "agent_id": command.agent_id,
        "trigger_source": command.trigger_source,
        "schedule_type": command.schedule_type,
        "planned_at": command.planned_at.isoformat() if command.planned_at else None,
        "category": command.category,
        "project_tag": command.project_tag,
        "repo_url": command.repo_url,
        "branch": command.branch,
        "pytest_options": command.pytest_options,
        "timeout": command.timeout,
        "cases": sorted(
            [
                {
                    "case_id": case_id,
                    "script_path": case_payload.get("script_path"),
                    "script_name": case_payload.get("script_name"),
                    "parameters": case_payload.get("parameters"),
                }
                for case_id, _, case_payload in zip(
                    command.case_ids,
                    command.case_configs,
                    command.case_payloads,
                )
            ],
            key=lambda item: (
                item["case_id"],
                item.get("script_path") or "",
                item.get("script_name") or "",
                json.dumps(
                    item.get("parameters") or {},
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            ),
        ),
    }
    normalized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_schedule(
    schedule_type: str | None,
    planned_at: datetime | None,
    now: datetime | None = None,
) -> tuple[str, datetime | None, str, bool]:
    """统一调度类型和状态。"""
    current_time = ensure_utc_datetime(now or datetime.now(timezone.utc))
    normalized_type = (schedule_type or "IMMEDIATE").upper()
    normalized_planned_at = ensure_utc_datetime(planned_at) if planned_at else None

    if normalized_type == "SCHEDULED":
        if normalized_planned_at is None:
            raise ValueError("planned_at is required when schedule_type is SCHEDULED")
        if normalized_planned_at <= current_time:
            return normalized_type, normalized_planned_at, ScheduleStatus.READY, True
        return normalized_type, normalized_planned_at, ScheduleStatus.PENDING, False

    return "IMMEDIATE", normalized_planned_at, ScheduleStatus.READY, True


def build_task_request_payload(command: DispatchExecutionTaskCommand) -> Dict[str, Any]:
    """构建任务级快照，保留完整 case 列表用于后续串行推进。"""
    return {
        "task_id": command.task_id,
        "dispatch_channel": command.dispatch_channel,
        "agent_id": command.agent_id,
        "trigger_source": command.trigger_source,
        "schedule_type": command.schedule_type,
        "planned_at": command.planned_at.isoformat() if command.planned_at else None,
        "category": command.category,
        "project_tag": command.project_tag,
        "repo_url": command.repo_url,
        "branch": command.branch,
        "pytest_options": command.pytest_options,
        "timeout": command.timeout,
        "cases": [
            {
                "case_id": case_id,
                "auto_case_id": auto_case_id,
                "script_entity_id": script_entity_id,
                "config": case_config,
                "payload_case_id": case_payload.get("case_id"),
                "script_path": case_payload.get("script_path"),
                "script_name": case_payload.get("script_name"),
                "parameters": case_payload.get("parameters"),
            }
            for case_id, auto_case_id, script_entity_id, case_config, case_payload in zip(
                command.case_ids,
                command.auto_case_ids,
                command.script_entity_ids,
                command.case_configs,
                command.case_payloads,
            )
        ],
        "created_by": command.created_by,
    }


def normalize_dispatch_channel(dispatch_channel: str | None) -> str:
    """固定使用 RabbitMQ 下发；忽略请求中的 dispatch_channel。"""
    if dispatch_channel is not None:
        normalized = dispatch_channel.strip().upper()
        if normalized and normalized != "RABBITMQ":
            logger.warning(
                f"Ignoring dispatch_channel '{dispatch_channel}', only RABBITMQ is supported"
            )
    return "RABBITMQ"


def ensure_actor_identity(actual_actor_id: str, expected_actor_id: str) -> None:
    """校验操作者是否就是任务创建者。"""
    if actual_actor_id != expected_actor_id:
        logger.warning(f"Actor ID mismatch: actor={actual_actor_id}, expected={expected_actor_id}")
        raise ValueError("Actor identity mismatch")


async def ensure_no_active_duplicate(dedup_key: str, excluded_task_id: str | None = None) -> None:
    """阻止创建或修改为相同业务载荷的未完成任务。"""
    query: Dict[str, Any] = {
        "dedup_key": dedup_key,
        "overall_status": {"$nin": list(FINAL_TASK_STATUSES)},
        "is_deleted": False,
    }
    if excluded_task_id:
        query["task_id"] = {"$ne": excluded_task_id}

    pending_task = await ExecutionTaskDoc.find_one(query)
    if pending_task:
        raise ValueError(
            f"Task already exists and is not finished: existing_task_id={pending_task.task_id}"
        )


def _get_system_config_sync(key: str) -> str | None:
    """同步读取系统配置值（用于非 async 上下文）。

    使用已有的 Beanie 连接（通过 asyncio.run_coroutine_threadsafe），
    避免每次创建新的 MongoDB 连接。
    """
    try:
        import asyncio
        from app.modules.system_config.repository.models import SystemConfigDoc
        from beanie.odm.utils.duplicate_key_error import get_exception

        loop = asyncio.get_event_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                _async_get_config(key), loop
            )
            return future.result(timeout=5)
        else:
            return asyncio.run(_async_get_config(key))
    except Exception as e:
        from app.shared.core.logger import log
        log.warning(f"Failed to read system config '{key}': {e}")
        return None


async def _async_get_config(key: str) -> str | None:
    """异步读取系统配置值（供 _get_system_config_sync 调用）"""
    doc = await SystemConfigDoc.find_one(
        SystemConfigDoc.config_key == key,
        SystemConfigDoc.is_active == True,
    )
    if doc and doc.config_value:
        return str(doc.config_value)
    return None


def build_rerun_command_from_payload(
    source_task_doc: Any,
    request: RerunTaskRequest,
    new_task_id: str,
    actor_id: str,
    dispatch_bindings: list[Any],
) -> DispatchExecutionTaskCommand:
    payload = dict(getattr(source_task_doc, "request_payload", {}) or {})
    cases = _extract_rerun_cases(payload, request)
    case_ids = [binding.case_id for binding in dispatch_bindings]
    script_entity_ids = [binding.script_entity_id for binding in dispatch_bindings]
    auto_case_ids = [case["auto_case_id"] for case in cases]
    case_configs = [dict(case.get("config") or {}) for case in cases]
    case_payloads = [
        {
            "case_id": binding.case_id,
            "script_path": binding.script_path,
            "script_name": binding.script_name,
            "parameters": dict(case.get("parameters") or {}),
        }
        for case, binding in zip(cases, dispatch_bindings)
    ]
    dispatch_channel = request.dispatch_channel or payload.get("dispatch_channel")
    agent_id = request.agent_id if request.agent_id is not None else payload.get("agent_id")
    schedule_type = request.schedule_type or "IMMEDIATE"
    planned_at = request.planned_at if request.schedule_type else None
    command = DispatchExecutionTaskCommand(
        task_id=new_task_id,
        source_task_id=getattr(source_task_doc, "task_id", None),
        dispatch_channel=dispatch_channel,
        agent_id=agent_id,
        created_by=actor_id,
        auto_case_ids=auto_case_ids,
        case_ids=case_ids,
        script_entity_ids=script_entity_ids,
        case_configs=case_configs,
        case_payloads=case_payloads,
        schedule_type=schedule_type,
        planned_at=planned_at,
        trigger_source=request.trigger_source if request.trigger_source is not None else payload.get("trigger_source"),
        category=request.category if request.category is not None else payload.get("category"),
        project_tag=request.project_tag if request.project_tag is not None else payload.get("project_tag"),
        repo_url=request.repo_url if request.repo_url is not None else payload.get("repo_url"),
        branch=request.branch if request.branch is not None else payload.get("branch"),
        pytest_options=_resolve_override_dict(request.pytest_options, payload, "pytest_options"),
        timeout=request.timeout if request.timeout is not None else payload.get("timeout"),
        attachments=[],
    )
    initialize_command(command)
    return command


def _extract_rerun_cases(payload: Dict[str, Any], request: RerunTaskRequest) -> list[dict[str, Any]]:
    if request.cases is None:
        return list(payload.get("cases", []))
    return [
        {
            "auto_case_id": item.auto_case_id,
            "config": dict(item.config),
            "parameters": dict(item.parameters),
        }
        for item in request.cases
    ]


def _resolve_override_dict(
    override_value: dict[str, Any] | None,
    payload: Dict[str, Any],
    field_name: str,
) -> dict[str, Any]:
    if override_value is not None:
        return dict(override_value)
    return dict(payload.get(field_name) or {})


def apply_task_command_to_doc(
    task_doc: ExecutionTaskDoc,
    command: DispatchExecutionTaskCommand,
    dedup_key: str,
    schedule_type: str,
    schedule_status: str,
    dispatch_status: str,
) -> None:
    """把任务命令映射到任务文档，复用创建/修改路径。"""
    assign_fields(
        task_doc,
        agent_id=command.agent_id,
        source_task_id=command.source_task_id,
        dispatch_channel=command.dispatch_channel,
        dedup_key=dedup_key,
        case_count=len(command.case_ids),
        reported_case_count=0,
        current_case_id=command.case_ids[0],
        current_case_index=0,
        planned_at=command.planned_at,
        schedule_type=schedule_type,
        schedule_status=schedule_status,
        dispatch_status=dispatch_status,
        request_payload=build_task_request_payload(command),
        dispatch_error=None,
        dispatch_response={},
        triggered_at=None,
        started_at=None,
        finished_at=None,
        last_callback_at=None,
        consume_status=ConsumeStatus.PENDING,
        consumed_at=None,
        overall_status=OverallStatus.QUEUED,
    )


def initialize_command(command: DispatchExecutionTaskCommand) -> None:
    """初始化命令的默认值和派生字段。

    替代原 Command.__post_init__ 的副作用操作。
    """
    _initialize_case_collections(command)
    _validate_case_collection_lengths(command)
    _apply_defaults(command)
    _initialize_dispatch_targets(command)


def _initialize_case_collections(command: DispatchExecutionTaskCommand) -> None:
    case_count = len(command.case_ids)
    if command.script_entity_ids is None:
        command.script_entity_ids = [None] * case_count
    if command.case_configs is None:
        command.case_configs = [{} for _ in range(case_count)]
    if command.case_payloads is None:
        command.case_payloads = [{} for _ in range(case_count)]


def _validate_case_collection_lengths(command: DispatchExecutionTaskCommand) -> None:
    case_count = len(command.case_ids)
    if len(command.auto_case_ids) != case_count:
        raise ValueError("auto_case_ids length must match case_ids length")
    if command.script_entity_ids is not None and len(command.script_entity_ids) != case_count:
        raise ValueError("script_entity_ids length must match case_ids length")
    if command.case_configs is not None and len(command.case_configs) != case_count:
        raise ValueError("case_configs length must match case_ids length")
    if command.case_payloads is not None and len(command.case_payloads) != case_count:
        raise ValueError("case_payloads length must match case_ids length")


def _apply_defaults(command: DispatchExecutionTaskCommand) -> None:
    from app.shared.config import get_settings
    from app.modules.system_config.service.config_service import ConfigService
    import asyncio

    execution_cfg = get_settings().execution
    command.dispatch_channel = "RABBITMQ"
    if isinstance(command.repo_url, str) and not command.repo_url.strip():
        command.repo_url = None
    if isinstance(command.branch, str) and not command.branch.strip():
        command.branch = None
    # git detached HEAD 状态会返回 "HEAD"，视为未配置，走系统默认分支
    if command.branch == "HEAD":
        command.branch = None
    # repo_url/branch：以系统配置（MongoDB）为准，config.yaml 作为最终兜底
    if command.repo_url is None:
        mongo_repo_url = _get_system_config_sync("execution.default_repo_url")
        command.repo_url = mongo_repo_url or execution_cfg.default_repo_url
    if command.branch is None:
        mongo_branch = _get_system_config_sync("execution.default_branch")
        command.branch = mongo_branch or execution_cfg.default_branch
    if command.category is None:
        command.category = ""
    if command.project_tag is None:
        command.project_tag = ""
    if command.pytest_options is None:
        command.pytest_options = {}
    if command.timeout is None:
        command.timeout = 0
    if command.attachments is None:
        command.attachments = []


def _initialize_dispatch_targets(command: DispatchExecutionTaskCommand) -> None:
    idx = command.dispatch_case_index
    if command.dispatch_case_id is None:
        command.dispatch_case_id = command.case_ids[idx]
    if command.dispatch_auto_case_id is None:
        command.dispatch_auto_case_id = command.auto_case_ids[idx]
    if command.dispatch_script_entity_id is None:
        command.dispatch_script_entity_id = command.script_entity_ids[idx] if command.script_entity_ids else None
    if command.dispatch_case_config is None:
        command.dispatch_case_config = command.case_configs[idx] if command.case_configs else {}


def build_dispatch_task_data(command: DispatchExecutionTaskCommand) -> Dict[str, Any]:
    """构建统一的任务下发数据。"""
    current_case_id = command.dispatch_case_id
    current_case_payload = command.case_payloads[command.dispatch_case_index] if command.case_payloads else {}
    from app.shared.kafka import load_kafka_config
    kafka_cfg = load_kafka_config()
    pytest_defaults = {
        "log_debug": False,
        "kafka_server": ",".join(kafka_cfg.bootstrap_servers),
        "kafka_topic": kafka_cfg.test_events_topic,
        "report_kafka": True,
        "maxfail": "3",
        "task_id": command.task_id,
    }
    pytest_options = {**pytest_defaults, **(command.pytest_options or {})}
    script_path = current_case_payload.get("script_path")
    script_name = current_case_payload.get("script_name")
    case_parameters = dict(current_case_payload.get("parameters") or {})
    modified_params, files_dict = _extract_and_enrich_file_params(case_parameters)
    if not script_path:
        raise ValueError(f"script_path is required for dispatch case: {current_case_id}")
    if not script_name:
        raise ValueError(f"script_name is required for dispatch case: {current_case_id}")

    return {
        "action": "create",
        "data": {
            "task_id": command.task_id,
            "trigger_source": command.trigger_source,
            "category": command.category,
            "project_tag": command.project_tag,
            "repo_url": command.repo_url,
            "branch": command.branch,
            "cases": [{
                "case_id": current_case_payload.get("case_id"),
                "script_path": script_path,
                "script_name": script_name,
                "parameters": modified_params,
            }],
            "files": files_dict,
            "pytest_options": pytest_options,
            "timeout": command.timeout,
            "is_proxy": command.is_proxy,
            "nc_pypi": command.nc_pypi,
        }
    }


def _extract_and_enrich_file_params(
    parameters: Dict[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """提取 file 类型参数到顶层 files 字段，返回 (modified_params, files_dict)。

    - modified_params: 原始参数，其中 file 类型字段值置为空字符串
    - files_dict: 顶层文件字典 {param_name: {url, sha256}}
    """
    result = dict(parameters)
    files_dict: Dict[str, Any] = {}

    from app.shared.minio import get_minio_client

    try:
        minio_client = get_minio_client()
        for key, value in result.items():
            if isinstance(value, dict) and value.get("type") == "file" and "object_name" in value:
                object_name = value.get("object_name")
                url = None
                try:
                    url = minio_client.presigned_get_object(object_name)
                except Exception as e:
                    logger.warning(
                        f"Failed to generate presigned URL for object '{object_name}': {e}"
                    )
                sha256 = value.get("sha256")
                files_dict[key] = {
                    "url": url,
                    "sha256": sha256,
                }
                result[key] = ""
    except Exception as e:
        logger.warning(
            f"MinIO client initialization failed, file params not extracted: {e}"
        )

    return result, files_dict
