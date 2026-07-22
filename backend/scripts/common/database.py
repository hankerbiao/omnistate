"""Shared MongoDB and Beanie runtime for operational scripts."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Sequence

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.shared.config import get_settings
from app.shared.infrastructure.bootstrap import initialize_beanie


async def close_client(client: AsyncMongoClient) -> None:
    """Close PyMongo clients across supported async driver versions."""
    close_result = client.close()
    if asyncio.iscoroutine(close_result):
        await close_result


@asynccontextmanager
async def database_runtime(
    *,
    document_models: Sequence[type[Any]] | None = None,
    sync_indexes: bool = False,
) -> AsyncIterator[Any]:
    """Connect, ping and initialize Beanie for a standalone script."""
    settings = get_settings()
    client = AsyncMongoClient(settings.mongodb.uri)
    try:
        await client.admin.command("ping")
        database = client[settings.mongodb.db_name]
        if document_models is None:
            await initialize_beanie(database, skip_indexes=not sync_indexes)
        else:
            await init_beanie(
                database=database,
                document_models=list(document_models),
                skip_indexes=not sync_indexes,
            )
        yield database
    finally:
        await close_client(client)
