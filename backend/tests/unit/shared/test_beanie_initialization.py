from __future__ import annotations

import pytest

from app.shared.infrastructure import bootstrap


async def test_initialize_beanie_accepts_explicit_index_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_init_beanie(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(bootstrap, "init_beanie", fake_init_beanie)
    monkeypatch.setattr(bootstrap, "get_document_models_list", lambda: [object])

    database = object()
    await bootstrap.initialize_beanie(database, skip_indexes=False)

    assert captured == {
        "database": database,
        "document_models": [object],
        "skip_indexes": False,
    }
