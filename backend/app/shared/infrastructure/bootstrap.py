from __future__ import annotations

from typing import Any

from beanie import init_beanie

from app.modules.attachments.repository.models import DOCUMENT_MODELS as ATTACHMENT_DOCUMENT_MODELS
from app.modules.auth.repository.models import DOCUMENT_MODELS as AUTH_DOCUMENT_MODELS
from app.modules.execution.repository.models import DOCUMENT_MODELS as EXECUTION_DOCUMENT_MODELS
from app.modules.test_specs.repository.models import DOCUMENT_MODELS as TEST_SPECS_DOCUMENT_MODELS
from app.modules.workflow.repository.models import (
    DOCUMENT_MODELS as WORKFLOW_DOCUMENT_MODELS,
    SysWorkflowConfigDoc,
    SysWorkflowStateDoc,
    SysWorkTypeDoc,
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
    ]


async def initialize_beanie(database: Any) -> None:
    await init_beanie(
        database=database,
        document_models=get_document_models(),
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
