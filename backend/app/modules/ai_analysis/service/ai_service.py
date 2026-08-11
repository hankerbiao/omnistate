"""AI 分析服务 - 使用系统配置的LLM分析测试用例集"""
import json
from typing import Any

from app.modules.system_config.constants.ai_analysis import (
    AI_PENDING_TASKS_SYSTEM_PROMPT_CONFIG_KEY,
    AI_PENDING_TASKS_USER_PROMPT_TEMPLATE_CONFIG_KEY,
)
from app.modules.system_config.service.config_service import ConfigService
from app.shared.ai.client import AIClient
from app.shared.core.logger import log


class AIService:
    """AI分析服务"""

    @staticmethod
    async def _build_pending_prompt(payload: dict[str, Any]) -> str:
        """使用数据库中的模板构建待处理任务分析提示词。"""
        stats = payload.get("stats", {})
        category_stats = payload.get("category_stats", [])
        items = payload.get("items", [])
        template = await ConfigService.get_config(
            AI_PENDING_TASKS_USER_PROMPT_TEMPLATE_CONFIG_KEY
        )
        return (
            template.replace("{stats}", json.dumps(stats, ensure_ascii=False))
            .replace("{category_stats}", json.dumps(category_stats, ensure_ascii=False))
            .replace("{items}", json.dumps(items, ensure_ascii=False))
        )

    @staticmethod
    async def analyze_pending_tasks(payload: dict[str, Any]) -> dict[str, Any]:
        """分析我的待处理任务。"""
        client = AIClient.get_instance()
        ai_config = await client.get_config()

        if not ai_config.get("enabled", True):
            stats = payload.get("stats", {})
            return {
                "summary": "AI 未启用，返回基于当前待办统计的静态分析。",
                "health_score": 0,
                "anomalies": [
                    {
                        "severity": "info",
                        "title": "AI 未启用",
                        "detail": "请在系统配置中开启 AI 后获得自动分析结果。",
                        "related_ids": [],
                    }
                ],
                "priority_items": [
                    {
                        "id": item.get("id", ""),
                        "title": item.get("title", ""),
                        "reason": "根据现有待处理清单优先展示",
                        "priority": "P1" if item.get("period") == "overdue" else "P2",
                    }
                    for item in payload.get("items", [])[:5]
                ],
                "recommendations": [
                    f"当前待处理总量 {stats.get('total', 0)}，请优先消化超期事项。",
                    "AI功能关闭时仅展示结构化建议，不返回模型推理结果。",
                ],
            }

        try:
            prompt = await AIService._build_pending_prompt(payload)
            content = await client.simple_chat(
                system_prompt=await ConfigService.get_config(
                    AI_PENDING_TASKS_SYSTEM_PROMPT_CONFIG_KEY
                ),
                user_content=prompt,
                temperature=float(ai_config.get("temperature", 0.3)),
                max_tokens=int(ai_config.get("max_tokens", 2048)),
            )
            result = AIClient._parse_json(content)
            if not isinstance(result, dict):
                raise ValueError("AI 返回格式错误")
            result.setdefault("summary", "待处理任务分析完成")
            result.setdefault("health_score", 60)
            result.setdefault("anomalies", [])
            result.setdefault("priority_items", [])
            result.setdefault("recommendations", [])
            return result
        except Exception as exc:
            log.error("待处理任务AI分析失败: {}", exc)
            return {
                "summary": f"AI 分析失败：{exc}",
                "health_score": 0,
                "anomalies": [
                    {
                        "severity": "critical",
                        "title": "AI 分析失败",
                        "detail": str(exc),
                        "related_ids": [],
                    }
                ],
                "priority_items": [],
                "recommendations": ["请检查 AI 配置和模型可用性后重试。"],
            }
    @staticmethod
    def _parse_response(content: str) -> dict[str, Any]:
        """解析LLM返回的JSON（委托给 AIClient._parse_json）。"""
        return AIClient._parse_json(content)
