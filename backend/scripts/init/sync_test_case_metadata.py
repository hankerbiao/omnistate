#!/usr/bin/env python3
"""Seed the global manual test-case metadata dictionary."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.test_specs.service.metadata_service import MetadataService  # noqa: E402
from scripts.common.database import database_runtime  # noqa: E402


async def main() -> None:
    async with database_runtime():
        await MetadataService.seed_defaults()
        print("测试用例元数据默认项同步完成")


if __name__ == "__main__":
    asyncio.run(main())
