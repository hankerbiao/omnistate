from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.init import sync_workflow


def test_merge_work_types_rejects_duplicate_code() -> None:
    work_types = {"REQUIREMENT": "需求"}

    with pytest.raises(ValueError, match="重复事项类型定义"):
        sync_workflow._merge_work_types(
            {"work_types": [["REQUIREMENT", "另一个名称"]]},
            work_types,
        )


@pytest.mark.parametrize("prune", [False, True])
async def test_workflow_cleanup_requires_explicit_prune(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    prune: bool,
) -> None:
    config_dir = tmp_path / "app" / "configs"
    config_dir.mkdir(parents=True)
    (config_dir / "workflow.json").write_text(
        json.dumps(
            {
                "work_types": [["TEST", "测试"]],
                "states": [{"code": "DRAFT", "name": "草稿"}],
                "workflow_configs": {},
            }
        ),
        encoding="utf-8",
    )
    cleanup_calls: list[str] = []

    async def no_op(*args, **kwargs) -> None:
        return None

    async def cleanup_work_types(*args, **kwargs) -> None:
        cleanup_calls.append("work_types")

    async def cleanup_configs(*args, **kwargs) -> None:
        cleanup_calls.append("configs")

    monkeypatch.setattr(sync_workflow, "ROOT", tmp_path)
    monkeypatch.setattr(sync_workflow, "_sync_work_types", no_op)
    monkeypatch.setattr(sync_workflow, "_sync_workflow_states", no_op)
    monkeypatch.setattr(sync_workflow, "_sync_workflow_configs", no_op)
    monkeypatch.setattr(sync_workflow, "_cleanup_removed_work_types", cleanup_work_types)
    monkeypatch.setattr(sync_workflow, "_cleanup_removed_workflow_configs", cleanup_configs)

    await sync_workflow.sync_workflow_config(prune=prune)

    assert cleanup_calls == (["work_types", "configs"] if prune else [])
