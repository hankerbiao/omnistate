#!/usr/bin/env python3
"""Migrate runtime settings from a full YAML configuration into MongoDB.

Run this before removing runtime sections from config.yaml. The command is
explicit and idempotent; application startup never seeds missing settings.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from beanie import init_beanie
from pymongo import AsyncMongoClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.system_config.repository.models import (  # noqa: E402
    SystemConfigDoc,
    SystemConfigHistoryDoc,
)
from app.modules.system_config.service.config_service import ConfigService, _flatten_config  # noqa: E402
from app.shared.config import BootstrapSettings, RuntimeSettings, clear_runtime_settings  # noqa: E402


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_source(base_path: Path, overlay_path: Path | None) -> dict[str, Any]:
    data = _load_yaml(base_path)
    if overlay_path is not None:
        data = _deep_merge(data, _load_yaml(overlay_path))
    return data


def _validate_runtime_source(source: dict[str, Any]) -> RuntimeSettings:
    """Require every runtime value to be explicit in the migration source."""
    runtime_source = {
        section: source.get(section, {})
        for section in RuntimeSettings.model_fields
    }
    expected_keys = set(_flatten_config(RuntimeSettings().model_dump()))
    provided_keys = set(_flatten_config(runtime_source))
    missing = sorted(expected_keys - provided_keys)
    unexpected = sorted(provided_keys - expected_keys)
    if missing:
        raise RuntimeError(
            "迁移源缺少运行配置，禁止使用代码默认值补齐: " + ", ".join(missing)
        )
    if unexpected:
        raise RuntimeError("迁移源包含未知运行配置: " + ", ".join(unexpected))
    return RuntimeSettings.model_validate(runtime_source, strict=True)


async def migrate(
    base_path: Path,
    overlay_path: Path | None,
    environment: str,
    *,
    metadata_only: bool = False,
) -> None:
    source = _load_source(base_path, overlay_path)
    bootstrap = BootstrapSettings(
        app=source.get("app", {}),
        mongodb=source.get("mongodb", {}),
        logging=source.get("logging", {}),
    )
    runtime = None
    if not metadata_only:
        runtime = _validate_runtime_source(source)

    os.environ["DML_ENV"] = environment
    client = AsyncMongoClient(bootstrap.mongodb.uri)
    try:
        await client.admin.command("ping")
        await init_beanie(
            database=client[bootstrap.mongodb.db_name],
            document_models=[SystemConfigDoc, SystemConfigHistoryDoc],
            skip_indexes=True,
        )

        runtime_count = 0
        ai_count = 0
        if runtime is not None:
            runtime_values = _flatten_config(runtime.model_dump())
            runtime_count = await ConfigService.import_configs(runtime_values, overwrite=True)
            ai_values = {
                item["config_key"]: ConfigService._parse_value(
                    item["config_value"], item["config_type"]
                )
                for item in ConfigService.AI_CONFIGS
            }
            ai_count = await ConfigService.import_configs(ai_values, overwrite=False)

        metadata_count = await ConfigService.sync_config_metadata()

        clear_runtime_settings()
        await ConfigService.load_runtime_settings(install=False)
        print(
            f"[{environment}] migrated {runtime_count} runtime values and "
            f"created {ai_count} missing AI values; synchronized {metadata_count} "
            f"metadata records in {bootstrap.mongodb.db_name}"
        )
    finally:
        clear_runtime_settings()
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="Full base YAML file")
    parser.add_argument("--overlay", type=Path, help="Optional environment overlay YAML")
    parser.add_argument("--environment", required=True, help="production, dev, test, ...")
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Synchronize catalog metadata without changing stored values",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(
        migrate(
            args.base,
            args.overlay,
            args.environment,
            metadata_only=args.metadata_only,
        )
    )


if __name__ == "__main__":
    main()
