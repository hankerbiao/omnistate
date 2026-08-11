"""AI 分析服务测试。"""

import pytest

from app.modules.ai_analysis.service.ai_service import AIService
from app.modules.system_config.constants.ai_analysis import (
    AI_PENDING_TASKS_USER_PROMPT_TEMPLATE_CONFIG_KEY,
)


@pytest.mark.asyncio
async def test_build_pending_prompt_uses_database_template(monkeypatch) -> None:
    template = "统计={stats}; 分类={category_stats}; 任务={items}; JSON={\"example\": true}"
    requested_keys: list[str] = []

    async def fake_get_config(key: str) -> str:
        requested_keys.append(key)
        return template

    monkeypatch.setattr(
        "app.modules.ai_analysis.service.ai_service.ConfigService.get_config",
        fake_get_config,
    )

    prompt = await AIService._build_pending_prompt(
        {
            "stats": {"total": 2},
            "category_stats": [{"category": "plan", "count": 1}],
            "items": [{"id": "TASK-1"}],
        }
    )

    assert requested_keys == [AI_PENDING_TASKS_USER_PROMPT_TEMPLATE_CONFIG_KEY]
    assert prompt == (
        '统计={"total": 2}; 分类=[{"category": "plan", "count": 1}]; '
        '任务=[{"id": "TASK-1"}]; JSON={"example": true}'
    )
