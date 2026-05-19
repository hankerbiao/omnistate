# 字段命名不一致问题报告

## 问题概述

后端 API 存在字段命名不一致的问题，导致前端和测试难以正确使用。

## 具体问题

### 1. Requirement 关联字段不一致

| 位置 | 字段名 | 说明 |
|------|--------|------|
| WorkItemResponse | `item_id` | 工作流项 ID |
| TestRequirementDoc | `req_id` | 需求业务编号 |
| TestRequirementDoc | `workflow_item_id` | 工作流项 ID（与 item_id 相同） |
| CreateTestCaseRequest | `ref_req_id` | 关联需求（期望 `req_id`） |

**问题描述**：
- 创建 WorkItem（包含 REQUIREMENT）返回的 `item_id` 对应 `TestRequirement.workflow_item_id`
- 创建 TestCase 需要传入 `ref_req_id`，但代码验证时查找 `TestRequirement.req_id`
- 这导致测试无法直接用 `item_id` 来关联 requirement

**示例**：
```python
# 创建 requirement
resp = await client.post("/api/v1/work-items/", json={...})
item_id = resp.json()["data"]["item_id"]  # 这是 workflow_item_id

# 创建 test case 失败 - ref_req_id 需要 req_id
resp = await client.post("/api/v1/test-cases", json={"ref_req_id": item_id})
# Error: "requirement not found"
```

**影响范围**：
- 测试用例创建
- 需求与用例关联查询
- 前端表单提交

### 2. 建议的修复方案

**方案 A：API 层面兼容**（推荐）
修改 `TestCaseService._ensure_requirement_exists` 方法，同时支持 `req_id` 和 `workflow_item_id`：
```python
# 尝试用 req_id 查找
existing = await TestRequirementDoc.find_one(
    TestRequirementDoc.req_id == req_id, ...
)
if not existing:
    # 尝试用 workflow_item_id 查找
    existing = await TestRequirementDoc.find_one(
        TestRequirementDoc.workflow_item_id == req_id, ...
    )
```

**方案 B：统一返回字段**
修改 WorkItemResponse 同时返回 `item_id` 和 `req_id`：
```python
class WorkItemResponse(BaseModel):
    item_id: str
    req_id: Optional[str] = None  # 仅对 REQUIREMENT 类型
```

**方案 C：文档明确说明**
在 API 文档中明确说明各字段的用途和关联关系。

## 建议

推荐 **方案 A**（API 兼容），因为：
1. 向后兼容，不破坏现有功能
2. 用户体验更好
3. 修改范围最小

## 相关文件

- `app/modules/test_specs/service/test_case_service.py:_ensure_requirement_exists`
- `app/modules/test_specs/schemas/test_case.py:CreateTestCaseRequest`
- `app/modules/workflow/schemas/work_item.py:WorkItemResponse`
- `tests/integration/test_workflow/test_requirement_case_link.py`

## 状态

- [ ] 待确认
- [ ] 计划修复
- [ ] 修复中
- [ ] 已修复