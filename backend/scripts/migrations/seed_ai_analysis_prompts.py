#!/usr/bin/env python3
"""Create missing AI analysis prompt configurations in MongoDB.

Existing prompt values are intentionally preserved so this command can be
rerun after prompts have been customized through the system-config API.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.system_config.constants.ai_analysis import (  # noqa: E402
    AI_ANALYSIS_PROMPT_CONFIGS,
)
from app.modules.system_config.repository.models import (  # noqa: E402
    SystemConfigDoc,
    SystemConfigHistoryDoc,
)
from app.modules.system_config.service.config_service import ConfigService  # noqa: E402
from scripts.common.database import database_runtime  # noqa: E402


async def seed_ai_analysis_prompts() -> int:
    """Create only missing AI analysis prompt configuration records."""
    values = {
        item["config_key"]: ConfigService._parse_value(
            item["config_value"],
            item["config_type"],
        )
        for item in AI_ANALYSIS_PROMPT_CONFIGS
    }
    async with database_runtime(
        document_models=[SystemConfigDoc, SystemConfigHistoryDoc]
    ):
        return await ConfigService.import_configs(values, overwrite=False)


def main() -> None:
    created = asyncio.run(seed_ai_analysis_prompts())
    print(f"Created {created} missing AI analysis prompt configuration(s).")


if __name__ == "__main__":
    main()
