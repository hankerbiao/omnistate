"""AI 分析服务 - 使用系统配置的LLM分析测试用例集"""
import json
from typing import Any

from app.modules.system_config.service.config_service import ConfigService
from app.modules.test_case_collection.repository.models import TestCaseCollectionDoc
from app.modules.test_specs.repository.models.test_case import TestCaseDoc
from app.modules.test_specs.repository.models.automation_test_case import AutomationTestCaseDoc
from app.shared.ai.client import AIClient
from app.shared.core.logger import log

# 系统角色提示词
SYSTEM_PROMPT = """你是一个专业的测试用例分析专家。你的任务是分析测试用例集的质量、冗余度和覆盖率。

请根据提供的测试用例数据，从以下三个维度进行分析，并以严格JSON格式返回结果：

## 1. 质量分析 (quality)
检查每个用例的以下方面：
- 标题/描述是否清晰明确
- 测试步骤是否完整（操作步骤 + 预期结果）
- 前置条件/后置条件是否完整
- 优先级是否合理

## 2. 冗余检测 (redundancy)
检查用例之间是否存在功能重复：
- 相同或高度相似的测试场景
- 可以合并的用例

## 3. 覆盖率分析 (coverage)
评估用例集对功能的覆盖程度：
- 识别测试盲区（缺失的场景）
- 建议补充的测试类型（边界值、异常场景等）

## 返回格式
你必须只返回一个JSON对象，不要包含额外说明或markdown：

```json
{
  "overall_score": 85,
  "quality": {
    "score": 80,
    "issues": [
      {"case_id": "TC-001", "field": "description", "severity": "warning", "message": "描述过于简略"}
    ]
  },
  "redundancy": {
    "score": 90,
    "duplicates": [
      {"case_id1": "TC-001", "case_id2": "TC-005", "similarity": 0.85, "reason": "测试步骤高度相似"}
    ]
  },
  "coverage": {
    "score": 75,
    "gaps": ["缺少边界值测试场景", "缺少异常输入测试"]
  },
  "recommendations": ["建议补充XX场景", "建议合并YY用例"]
}
```

- overall_score: 0-100的综合评分
- score: 每个维度的评分
- severity: critical/warning/info
- similarity: 0-1之间的相似度
"""


class AIService:
    """AI分析服务"""

    @staticmethod
    async def _fetch_collection_cases(collection_id: str) -> list[dict]:
        """根据集合ID获取用例数据"""
        from fastapi import HTTPException

        collection = await TestCaseCollectionDoc.find_one(
            TestCaseCollectionDoc.collection_id == collection_id
        )
        if not collection:
            raise HTTPException(status_code=404, detail=f"集合不存在: {collection_id}")

        cases_data = []

        # 获取手工用例
        if collection.case_ids:
            for cid in collection.case_ids:
                doc = await TestCaseDoc.find_one(TestCaseDoc.case_id == cid)
                if doc:
                    case_info = {
                        "id": doc.case_id,
                        "title": doc.title,
                        "type": "manual",
                        "priority": doc.priority or "",
                        "status": doc.status if hasattr(doc, "status") else "",
                        "tags": doc.tags or [],
                    }
                    cases_data.append(case_info)

        # 获取自动化用例
        if collection.auto_case_ids:
            for aid in collection.auto_case_ids:
                doc = await AutomationTestCaseDoc.find_one(
                    AutomationTestCaseDoc.auto_case_id == aid
                )
                if doc:
                    case_info = {
                        "id": doc.auto_case_id,
                        "title": doc.name if hasattr(doc, "name") else aid,
                        "type": "auto",
                        "status": doc.status if hasattr(doc, "status") else "",
                        "tags": doc.tags if hasattr(doc, "tags") else [],
                    }
                    cases_data.append(case_info)

        if not cases_data:
            raise HTTPException(status_code=400, detail="集合中无用例数据")

        return cases_data

    @staticmethod
    async def analyze_collection_by_id(
        collection_id: str,
        analysis_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """根据集合ID获取数据并执行AI分析"""
        cases_data = await AIService._fetch_collection_cases(collection_id)
        return await AIService.analyze_collection(
            collection_id=collection_id,
            cases_data=cases_data,
            analysis_types=analysis_types,
        )

    @staticmethod
    async def analyze_collection(
        collection_id: str,
        cases_data: list[dict],
        analysis_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """分析用例集

        Args:
            collection_id: 集合ID
            cases_data: 用例数据列表
            analysis_types: 分析类型，默认全部

        Returns:
            分析结果字典
        """
        if analysis_types is None:
            analysis_types = ["quality", "redundancy", "coverage"]

        client = AIClient.get_instance()
        ai_config = await client.get_config()

        if not ai_config.get("enabled", True):
            return {
                "collection_id": collection_id,
                "overall_score": 0,
                "quality": {"score": 0, "issues": []},
                "redundancy": {"score": 100, "duplicates": []},
                "coverage": {"score": 0, "gaps": []},
                "recommendations": ["AI分析服务未启用，请先在系统配置中设置LLM参数"],
            }

        try:
            max_cases = int(await ConfigService.get_config("ai.max_cases", 20))
            truncated = len(cases_data) > max_cases
            limited_cases = cases_data[:max_cases]
            if truncated:
                log.warning(f"用例数({len(cases_data)})超过限制({max_cases})，仅分析前{max_cases}个")

            prompt = AIService._build_prompt(limited_cases, analysis_types)
            model = ai_config.get("model", "unknown")

            log.info(f"正在调用LLM分析用例集 {collection_id}，模型={model}，用例数={len(limited_cases)}")

            content = await client.simple_chat(
                system_prompt=SYSTEM_PROMPT,
                user_content=prompt,
                temperature=float(ai_config.get("temperature", 0.3)),
                max_tokens=int(ai_config.get("max_tokens", 4096)),
            )

            result = AIService._parse_response(content)
            result["collection_id"] = collection_id
            return result

        except RuntimeError as e:
            log.error(f"AI分析失败(配置): {e}")
            return {
                "collection_id": collection_id,
                "overall_score": 0,
                "quality": {"score": 0, "issues": [{"case_id": "", "field": "system", "severity": "error", "message": f"AI分析服务不可用: {str(e)}"}]},
                "redundancy": {"score": 100, "duplicates": []},
                "coverage": {"score": 0, "gaps": []},
                "recommendations": [f"AI分析服务不可用: {str(e)}"],
            }
        except Exception as e:
            log.error(f"AI分析失败: {e}")
            return {
                "collection_id": collection_id,
                "overall_score": 0,
                "quality": {"score": 0, "issues": [{"case_id": "", "field": "system", "severity": "error", "message": f"AI分析调用失败: {str(e)}"}]},
                "redundancy": {"score": 100, "duplicates": []},
                "coverage": {"score": 0, "gaps": []},
                "recommendations": [f"AI分析失败: {str(e)}，请检查LLM配置"],
            }

    @staticmethod
    def _build_prompt(cases_data: list[dict], analysis_types: list[str]) -> str:
        """构建分析Prompt

        Args:
            cases_data: 用例数据列表，每项包含 id, title, description, steps, pre_condition, post_condition 等
            analysis_types: 分析类型列表
        """
        types_desc = {
            "quality": "- 质量分析：评估每个用例的描述完整性、步骤清晰度",
            "redundancy": "- 冗余检测：检查用例之间的功能重复",
            "coverage": "- 覆盖率分析：评估测试覆盖盲区",
        }

        enabled_types = [types_desc[t] for t in analysis_types if t in types_desc]
        types_text = "\n".join(enabled_types) if enabled_types else "\n".join(types_desc.values())

        # 格式化用例数据
        cases_text = json.dumps(cases_data, ensure_ascii=False, indent=2)

        prompt = f"""请分析以下测试用例集：

需要分析的维度：
{types_text}

测试用例数据：
{cases_text}

请严格按照要求的JSON格式返回分析结果。"""

        return prompt

    @staticmethod
    def _parse_response(content: str) -> dict[str, Any]:
        """解析LLM返回的JSON（委托给 AIClient._parse_json）。"""
        return AIClient._parse_json(content)
