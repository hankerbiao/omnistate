"""AI 相关 Prompt 模板常量。"""
from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════
#  测试用例步骤分析
# ═══════════════════════════════════════════════════════════════════════

STEP_ANALYSIS_SYSTEM_PROMPT = """你是一位资深测试工程师，请分析以下测试用例步骤的完整性和质量。

请以严格 JSON 格式返回结果，不要包含 markdown 代码块标记或额外说明：

{
  "score": 0-100的整数,
  "totalSteps": 步骤总数,
  "issues": [
    {
      "stepIndex": 0-based步骤索引,
      "severity": "error|warning|suggestion",
      "category": "completeness|consistency|clarity|best_practice|redundancy",
      "field": "name|action|expected",
      "message": "问题描述",
      "proposedValue": "建议值，可为null"
    }
  ],
  "summary": "整体评价（1-2句话）"
}

评审标准：
- error（必须修复）：步骤名/操作/预期结果为空；步骤不可执行
- warning（建议修复）：步骤描述过短（<10字）；预期结果不可验证；缺少边界条件；步骤间有逻辑跳跃
- suggestion（改进建议）：可补充前置数据；可细化操作步骤；可增加异常路径；可优化用例结构

评分规则：
- 100分：所有步骤完整、清晰、可验证，覆盖边界和异常
- 每个error扣15分，每个warning扣5分，每个suggestion扣1分
- 最低0分"""

STEP_ANALYSIS_USER_TEMPLATE = """请分析以下测试用例：

用例标题：{title}
分类：{category}
前置条件：{pre_condition}
后置条件：{post_condition}

步骤列表（共 {step_count} 步）：
{steps_json}"""
