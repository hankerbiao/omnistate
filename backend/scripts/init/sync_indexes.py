#!/usr/bin/env python3
"""Synchronize indexes for every registered Beanie document model."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.infrastructure.bootstrap import get_document_models_list  # noqa: E402
from scripts.common.database import database_runtime  # noqa: E402


async def main() -> None:
    model_count = len(get_document_models_list())
    async with database_runtime(sync_indexes=True):
        print(f"MongoDB 索引同步完成，共注册 {model_count} 个文档模型")


if __name__ == "__main__":
    asyncio.run(main())
