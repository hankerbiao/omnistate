from __future__ import annotations

import os
from typing import Any

from beanie import init_beanie

from app.modules.attachments.repository.models import DOCUMENT_MODELS as ATTACHMENT_DOCUMENT_MODELS
from app.modules.auth.repository.models import DOCUMENT_MODELS as AUTH_DOCUMENT_MODELS
from app.modules.execution.repository.models import DOCUMENT_MODELS as EXECUTION_DOCUMENT_MODELS
from app.modules.execution_plan.repository.models import DOCUMENT_MODELS as EXECUTION_PLAN_DOCUMENT_MODELS
from app.modules.test_specs.repository.models import DOCUMENT_MODELS as TEST_SPECS_DOCUMENT_MODELS
from app.modules.workflow.repository.models import (
    DOCUMENT_MODELS as WORKFLOW_DOCUMENT_MODELS,
    SysWorkflowConfigDoc,
    SysWorkflowStateDoc,
    SysWorkTypeDoc,
)
from app.modules.test_case_collection.repository.models import (
    DOCUMENT_MODELS as COLLECTION_DOCUMENT_MODELS,
)
from app.modules.system_config.repository.models import (
    DOCUMENT_MODELS as SYSTEM_CONFIG_DOCUMENT_MODELS,
)
from app.modules.project.repository.models import (
    DOCUMENT_MODELS as PROJECT_DOCUMENT_MODELS,
)
from app.shared.core.logger import log


def get_document_models() -> list[type[Any]]:
    """Return Beanie document models in startup registration order."""
    return [
        *WORKFLOW_DOCUMENT_MODELS,
        *TEST_SPECS_DOCUMENT_MODELS,
        *EXECUTION_DOCUMENT_MODELS,
        *AUTH_DOCUMENT_MODELS,
        *ATTACHMENT_DOCUMENT_MODELS,
        *EXECUTION_PLAN_DOCUMENT_MODELS,
        *COLLECTION_DOCUMENT_MODELS,
        *SYSTEM_CONFIG_DOCUMENT_MODELS,
        *PROJECT_DOCUMENT_MODELS,
    ]


async def initialize_beanie(database: Any) -> None:
    # 生产环境跳过索引同步，索引由部署脚本/CI 管理。
    # 开发环境或显式设置 SKIP_INDEX_SYNC=0 时仍同步索引。
    skip_indexes = os.getenv("SKIP_INDEX_SYNC", "1") == "1"

    await init_beanie(
        database=database,
        document_models=get_document_models(),
        skip_indexes=skip_indexes,
    )

    if skip_indexes:
        log.info(
            "Beanie 索引同步已跳过（SKIP_INDEX_SYNC=1），"
            "如需同步索引请运行: python app/init_mongodb.py 或设置 SKIP_INDEX_SYNC=0"
        )


async def validate_workflow_consistency() -> None:
    """启动时校验 workflow 基础配置，避免脏配置进入运行期。"""
    work_types = await SysWorkTypeDoc.find_all().to_list()
    states = await SysWorkflowStateDoc.find_all().to_list()
    configs = await SysWorkflowConfigDoc.find_all().to_list()

    # 对未初始化环境做兼容：仅告警，不阻断服务启动。
    if not work_types and not states and not configs:
        log.warning(
            "workflow consistency check skipped: workflow configs are empty, "
            "run `python app/init_mongodb.py` to initialize"
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
