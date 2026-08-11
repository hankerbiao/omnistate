from __future__ import annotations

from app.modules.system_config.constants.ai_analysis import (
    AI_ANALYSIS_PROMPT_CONFIGS,
    AI_PENDING_TASKS_SYSTEM_PROMPT_CONFIG_KEY,
    AI_PENDING_TASKS_USER_PROMPT_TEMPLATE_CONFIG_KEY,
)


def test_ai_analysis_prompt_catalog_contains_both_pending_task_prompts() -> None:
    config_keys = {item["config_key"] for item in AI_ANALYSIS_PROMPT_CONFIGS}

    assert config_keys == {
        AI_PENDING_TASKS_SYSTEM_PROMPT_CONFIG_KEY,
        AI_PENDING_TASKS_USER_PROMPT_TEMPLATE_CONFIG_KEY,
    }
