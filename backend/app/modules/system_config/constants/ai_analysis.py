"""AI 分析提示词的数据库配置定义。"""

AI_PENDING_TASKS_SYSTEM_PROMPT_CONFIG_KEY = "ai.pending_tasks.system_prompt"
AI_PENDING_TASKS_USER_PROMPT_TEMPLATE_CONFIG_KEY = "ai.pending_tasks.user_prompt_template"

AI_ANALYSIS_PROMPT_CONFIGS = [
    {
        "config_key": AI_PENDING_TASKS_SYSTEM_PROMPT_CONFIG_KEY,
        "config_value": (
            "你是一个严谨的任务运营分析专家，擅长从待处理任务看板识别"
            "积压、异常和优先级建议。只能输出严格 JSON。"
        ),
        "config_type": "string",
        "category": "ai",
        "description": "我的待处理任务 AI 分析系统提示词",
        "needs_restart": False,
    },
    {
        "config_key": AI_PENDING_TASKS_USER_PROMPT_TEMPLATE_CONFIG_KEY,
        "config_value": """请分析以下我的待处理任务看板快照，判断当前待办结构是否健康，识别异常积压、超期风险、分类失衡和优先级建议。

统计摘要: {stats}

分类占比: {category_stats}

重点任务列表: {items}

请只返回严格 JSON，字段如下：
{
  "summary": "一句话总结",
  "health_score": 0,
  "anomalies": [{"severity": "warning", "title": "...", "detail": "...", "related_ids": ["..."]}],
  "priority_items": [{"id": "...", "title": "...", "reason": "...", "priority": "P1"}],
  "recommendations": ["..."]
}""",
        "config_type": "string",
        "category": "ai",
        "description": "我的待处理任务 AI 分析用户提示词模板（支持 {stats}、{category_stats}、{items}）",
        "needs_restart": False,
    },
]
