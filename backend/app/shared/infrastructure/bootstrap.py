from __future__ import annotations

import importlib
import os
from typing import Any

from beanie import init_beanie

from app.shared.infrastructure.document_registry import get_document_models
from app.shared.core.logger import log


# 所有需要注册 Beanie 文档模型的模块路径
_DOCUMENT_MODULE_PATHS = [
    "app.modules.workflow.repository.models",
    "app.modules.test_specs.repository.models",
    "app.modules.execution.repository.models",
    "app.modules.auth.repository.models",
    "app.modules.attachments.repository.models",
    "app.modules.execution_plan.repository.models",
    "app.modules.test_case_collection.repository.models",
    "app.modules.system_config.repository.models",
    "app.modules.project.repository.models",
    "app.modules.notification.repository.models",
]


def _ensure_all_models_imported() -> None:
    """确保所有模块的 repository/models/__init__.py 被导入，
    从而触发 register_document_model() 将模型注册到注册表。"""
    for module_path in _DOCUMENT_MODULE_PATHS:
        try:
            importlib.import_module(module_path)
        except ImportError as e:
            log.warning(f"Failed to import {module_path}: {e}")


def get_document_models_list() -> list[type[Any]]:
    """Return Beanie document models in startup registration order."""
    _ensure_all_models_imported()
    return get_document_models()


async def initialize_beanie(database: Any) -> None:
    skip_indexes = os.getenv("SKIP_INDEX_SYNC", "1") == "1"

    await init_beanie(
        database=database,
        document_models=get_document_models_list(),
        skip_indexes=skip_indexes,
    )

    if skip_indexes:
        log.info(
            "Beanie 索引同步已跳过（SKIP_INDEX_SYNC=1），"
            "如需同步索引请运行: python scripts/init/init_mongodb.py 或设置 SKIP_INDEX_SYNC=0"
        )


async def validate_workflow_consistency() -> None:
    """启动时校验 workflow 基础配置，避免脏配置进入运行期。"""
    from app.modules.workflow.repository.models import SysWorkTypeDoc, SysWorkflowStateDoc, SysWorkflowConfigDoc

    work_types = await SysWorkTypeDoc.find_all().to_list()
    states = await SysWorkflowStateDoc.find_all().to_list()
    configs = await SysWorkflowConfigDoc.find_all().to_list()

    if not work_types and not states and not configs:
        log.warning(
            "workflow consistency check skipped: workflow configs are empty, "
            "run `python scripts/init/init_mongodb.py` to initialize"
        )
        return

    if not work_types:
        raise RuntimeError("workflow consistency check failed: no work types configured")
    if not states:
        raise RuntimeError("workflow consistency check failed: no states configured")

    type_codes = {doc.code for doc in work_types}
    state_codes = {doc.code for doc in states}
    errors: list[str] = []

    for cfg in configs:
        if cfg.type_code not in type_codes:
            errors.append(f"unknown type_code={cfg.type_code}")
        if cfg.from_state not in state_codes:
            errors.append(f"unknown from_state={cfg.from_state}")
        if cfg.to_state not in state_codes:
            errors.append(f"unknown to_state={cfg.to_state}")

    if errors:
        raise RuntimeError(
            "workflow consistency check failed: " + "; ".join(sorted(set(errors)))
        )
