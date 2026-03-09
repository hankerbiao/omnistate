#!/usr/bin/env python3
"""
数据一致性审计脚本 - Phase 7

此脚本审计工作流系统的数据一致性，检查并报告以下6种不一致性：

1. find linked business records missing `workflow_item_id`
2. find `Requirement.status != WorkItem.current_state`
3. find `TestCase.status != WorkItem.current_state`
4. find business docs deleted but work items active
5. find work items deleted but business docs active
6. find test cases whose `ref_req_id` and parent work item relation disagree

Usage:
    python scripts/audit_workflow_consistency.py [--output=json|console] [--fix-suggestions]
"""

import asyncio
import argparse
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from beanie import PydanticObjectId

from app.modules.workflow.repository.models.business import BusWorkItemDoc
from app.modules.test_specs.repository.models.requirement import TestRequirementDoc
from app.modules.test_specs.repository.models.test_case import TestCaseDoc
from app.shared.core.logger import log as logger


class ConsistencyIssue(BaseModel):
    """一致性问题的数据模型"""
    issue_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    title: str
    description: str
    affected_count: int
    sample_data: List[Dict[str, Any]]
    suggestions: List[str]
    repairable: bool = True


class ConsistencyAuditReport(BaseModel):
    """数据一致性审计报告"""
    audit_timestamp: datetime
    total_issues: int
    issues_by_severity: Dict[str, int]
    issues: List[ConsistencyIssue]
    summary: Dict[str, str]


class WorkflowConsistencyAuditor:
    """工作流一致性审计器"""

    def __init__(self):
        self.issues: List[ConsistencyIssue] = []
        self.sample_size = 10  # 用于展示的样本数量

    async def audit_all(self) -> ConsistencyAuditReport:
        """执行所有一致性检查"""
        logger.info("开始工作流数据一致性审计...")

        # 执行6种检查
        await self._check_missing_workflow_item_ids()
        await self._check_requirement_status_consistency()
        await self._check_test_case_status_consistency()
        await self._check_deleted_business_active_work_items()
        await self._check_deleted_work_items_active_business()
        await self._check_test_case_requirement_relationship()

        # 生成报告
        report = self._generate_report()
        logger.info(f"数据一致性审计完成，发现 {report.total_issues} 个问题")

        return report

    async def _check_missing_workflow_item_ids(self):
        """检查缺少 workflow_item_id 的业务记录"""
        logger.info("检查缺少 workflow_item_id 的业务记录...")

        # 检查需求
        requirements_missing_id = await TestRequirementDoc.find(
            {"workflow_item_id": None, "is_deleted": False}
        ).to_list()

        # 检查测试用例
        test_cases_missing_id = await TestCaseDoc.find(
            {"workflow_item_id": None, "is_deleted": False}
        ).to_list()

        # 合并问题
        all_missing = []
        for req in requirements_missing_id[:self.sample_size]:
            all_missing.append({
                "type": "requirement",
                "id": str(req.id),
                "req_id": req.req_id,
                "title": req.title,
                "workflow_item_id": req.workflow_item_id
            })

        for tc in test_cases_missing_id[:self.sample_size]:
            all_missing.append({
                "type": "test_case",
                "id": str(tc.id),
                "case_id": tc.case_id,
                "title": tc.title,
                "workflow_item_id": tc.workflow_item_id
            })

        if all_missing:
            issue = ConsistencyIssue(
                issue_type="missing_workflow_item_id",
                severity="CRITICAL",
                title="缺少工作流ID的关联业务记录",
                description="发现缺少 workflow_item_id 的业务记录，这些记录无法与工作流状态关联",
                affected_count=len(requirements_missing_id) + len(test_cases_missing_id),
                sample_data=all_missing,
                suggestions=[
                    "为每个缺失的工作流ID创建对应的 BusWorkItemDoc",
                    "更新业务记录的 workflow_item_id 字段",
                    "确保工作流ID的唯一性和正确性"
                ]
            )
            self.issues.append(issue)

    async def _check_requirement_status_consistency(self):
        """检查需求状态与工作流状态的一致性"""
        logger.info("检查需求状态与工作流状态的一致性...")

        # 获取所有非删除的需求及其工作流项
        requirements = await TestRequirementDoc.find({"is_deleted": False}).to_list()

        inconsistent_requirements = []
        for req in requirements:
            if req.workflow_item_id:
                try:
                    work_item = await BusWorkItemDoc.get(req.workflow_item_id)
                    if work_item and req.status != work_item.current_state:
                        inconsistent_requirements.append({
                            "requirement_id": str(req.id),
                            "req_id": req.req_id,
                            "requirement_status": req.status,
                            "work_item_id": str(work_item.id),
                            "work_item_state": work_item.current_state
                        })
                except Exception as e:
                    # 工作流项不存在或无法访问
                    inconsistent_requirements.append({
                        "requirement_id": str(req.id),
                        "req_id": req.req_id,
                        "requirement_status": req.status,
                        "work_item_id": req.workflow_item_id,
                        "work_item_state": "NOT_FOUND",
                        "error": str(e)
                    })

        if inconsistent_requirements:
            issue = ConsistencyIssue(
                issue_type="requirement_status_inconsistency",
                severity="HIGH",
                title="需求状态与工作流状态不一致",
                description="发现需求的状态与其关联工作流项的当前状态不匹配",
                affected_count=len(inconsistent_requirements),
                sample_data=inconsistent_requirements[:self.sample_size],
                suggestions=[
                    "同步需求状态到工作流状态",
                    "验证工作流状态转换的规则",
                    "检查状态同步机制是否正常工作"
                ]
            )
            self.issues.append(issue)

    async def _check_test_case_status_consistency(self):
        """检查测试用例状态与工作流状态的一致性"""
        logger.info("检查测试用例状态与工作流状态的一致性...")

        # 获取所有非删除的测试用例及其工作流项
        test_cases = await TestCaseDoc.find({"is_deleted": False}).to_list()

        inconsistent_test_cases = []
        for tc in test_cases:
            if tc.workflow_item_id:
                try:
                    work_item = await BusWorkItemDoc.get(tc.workflow_item_id)
                    if work_item and tc.status != work_item.current_state:
                        inconsistent_test_cases.append({
                            "test_case_id": str(tc.id),
                            "case_id": tc.case_id,
                            "test_case_status": tc.status,
                            "work_item_id": str(work_item.id),
                            "work_item_state": work_item.current_state
                        })
                except Exception as e:
                    # 工作流项不存在或无法访问
                    inconsistent_test_cases.append({
                        "test_case_id": str(tc.id),
                        "case_id": tc.case_id,
                        "test_case_status": tc.status,
                        "work_item_id": tc.workflow_item_id,
                        "work_item_state": "NOT_FOUND",
                        "error": str(e)
                    })

        if inconsistent_test_cases:
            issue = ConsistencyIssue(
                issue_type="test_case_status_inconsistency",
                severity="HIGH",
                title="测试用例状态与工作流状态不一致",
                description="发现测试用例的状态与其关联工作流项的当前状态不匹配",
                affected_count=len(inconsistent_test_cases),
                sample_data=inconsistent_test_cases[:self.sample_size],
                suggestions=[
                    "同步测试用例状态到工作流状态",
                    "验证工作流状态转换的规则",
                    "检查状态同步机制是否正常工作"
                ]
            )
            self.issues.append(issue)

    async def _check_deleted_business_active_work_items(self):
        """检查业务文档被删除但工作项仍活跃的情况"""
        logger.info("检查业务文档被删除但工作项仍活跃的情况...")

        # 检查被删除的需求对应的活跃工作项
        deleted_requirements = await TestRequirementDoc.find({"is_deleted": True}).to_list()
        orphaned_work_items_requirements = []

        for req in deleted_requirements:
            if req.workflow_item_id:
                try:
                    work_item = await BusWorkItemDoc.get(req.workflow_item_id)
                    if work_item and not work_item.is_deleted:
                        orphaned_work_items_requirements.append({
                            "requirement_id": str(req.id),
                            "req_id": req.req_id,
                            "work_item_id": str(work_item.id),
                            "work_item_title": work_item.title,
                            "work_item_state": work_item.current_state
                        })
                except Exception:
                    pass

        # 检查被删除的测试用例对应的活跃工作项
        deleted_test_cases = await TestCaseDoc.find({"is_deleted": True}).to_list()
        orphaned_work_items_test_cases = []

        for tc in deleted_test_cases:
            if tc.workflow_item_id:
                try:
                    work_item = await BusWorkItemDoc.get(tc.workflow_item_id)
                    if work_item and not work_item.is_deleted:
                        orphaned_work_items_test_cases.append({
                            "test_case_id": str(tc.id),
                            "case_id": tc.case_id,
                            "work_item_id": str(work_item.id),
                            "work_item_title": work_item.title,
                            "work_item_state": work_item.current_state
                        })
                except Exception:
                    pass

        total_orphaned = len(orphaned_work_items_requirements) + len(orphaned_work_items_test_cases)

        if total_orphaned > 0:
            all_orphaned = (
                orphaned_work_items_requirements + orphaned_work_items_test_cases
            )[:self.sample_size]

            issue = ConsistencyIssue(
                issue_type="deleted_business_active_work_items",
                severity="MEDIUM",
                title="业务文档被删除但工作项仍活跃",
                description="发现业务文档已被删除，但其关联的工作流项仍然活跃",
                affected_count=total_orphaned,
                sample_data=all_orphaned,
                suggestions=[
                    "将活跃的工作流项标记为已删除",
                    "或恢复相应的业务文档（如果误删）",
                    "检查删除逻辑确保级联删除的一致性"
                ]
            )
            self.issues.append(issue)

    async def _check_deleted_work_items_active_business(self):
        """检查工作项被删除但业务文档仍活跃的情况"""
        logger.info("检查工作项被删除但业务文档仍活跃的情况...")

        # 获取所有已删除的工作项
        deleted_work_items = await BusWorkItemDoc.find({"is_deleted": True}).to_list()

        orphaned_business_docs = []

        for work_item in deleted_work_items:
            # 检查关联的需求
            requirements = await TestRequirementDoc.find(
                {"workflow_item_id": str(work_item.id), "is_deleted": False}
            ).to_list()

            for req in requirements:
                orphaned_business_docs.append({
                    "work_item_id": str(work_item.id),
                    "work_item_title": work_item.title,
                    "business_type": "requirement",
                    "business_id": str(req.id),
                    "req_id": req.req_id
                })

            # 检查关联的测试用例
            test_cases = await TestCaseDoc.find(
                {"workflow_item_id": str(work_item.id), "is_deleted": False}
            ).to_list()

            for tc in test_cases:
                orphaned_business_docs.append({
                    "work_item_id": str(work_item.id),
                    "work_item_title": work_item.title,
                    "business_type": "test_case",
                    "business_id": str(tc.id),
                    "case_id": tc.case_id
                })

        if orphaned_business_docs:
            issue = ConsistencyIssue(
                issue_type="deleted_work_items_active_business",
                severity="MEDIUM",
                title="工作项被删除但业务文档仍活跃",
                description="发现工作流项已被删除，但其关联的业务文档仍然活跃",
                affected_count=len(orphaned_business_docs),
                sample_data=orphaned_business_docs[:self.sample_size],
                suggestions=[
                    "将活跃的业务文档标记为已删除",
                    "或恢复相应的工作流项（如果误删）",
                    "检查删除逻辑确保级联删除的一致性"
                ]
            )
            self.issues.append(issue)

    async def _check_test_case_requirement_relationship(self):
        """检查测试用例的 ref_req_id 和父工作项关系的一致性"""
        logger.info("检查测试用例与需求的关联关系...")

        test_cases = await TestCaseDoc.find({"is_deleted": False}).to_list()

        inconsistent_relationships = []

        for tc in test_cases:
            # 查找对应的需求
            try:
                requirement = await TestRequirementDoc.find_one(
                    {"req_id": tc.ref_req_id, "is_deleted": False}
                )

                if requirement:
                    # 检查测试用例的工作流项和需求的工作流项是否关联
                    if tc.workflow_item_id and requirement.workflow_item_id:
                        tc_work_item = await BusWorkItemDoc.get(tc.workflow_item_id)
                        req_work_item = await BusWorkItemDoc.get(requirement.workflow_item_id)

                        if tc_work_item and req_work_item:
                            # 检查是否应该是父子关系（测试用例的工作流项应该是需求的子项）
                            if tc_work_item.parent_item_id != requirement.workflow_item_id:
                                inconsistent_relationships.append({
                                    "test_case_id": str(tc.id),
                                    "case_id": tc.case_id,
                                    "ref_req_id": tc.ref_req_id,
                                    "requirement_work_item_id": requirement.workflow_item_id,
                                    "test_case_work_item_id": tc.workflow_item_id,
                                    "expected_parent": requirement.workflow_item_id,
                                    "actual_parent": tc_work_item.parent_item_id
                                })
                    else:
                        # 缺少工作流项关联
                        inconsistent_relationships.append({
                            "test_case_id": str(tc.id),
                            "case_id": tc.case_id,
                            "ref_req_id": tc.ref_req_id,
                            "requirement_work_item_id": requirement.workflow_item_id,
                            "test_case_work_item_id": tc.workflow_item_id,
                            "issue": "missing_workflow_associations"
                        })
                else:
                    # 引用的需求不存在
                    inconsistent_relationships.append({
                        "test_case_id": str(tc.id),
                        "case_id": tc.case_id,
                        "ref_req_id": tc.ref_req_id,
                        "issue": "referenced_requirement_not_found"
                    })

            except Exception as e:
                inconsistent_relationships.append({
                    "test_case_id": str(tc.id),
                    "case_id": tc.case_id,
                    "ref_req_id": tc.ref_req_id,
                    "error": str(e)
                })

        if inconsistent_relationships:
            issue = ConsistencyIssue(
                issue_type="test_case_requirement_relationship_inconsistency",
                severity="MEDIUM",
                title="测试用例与需求关联关系不一致",
                description="发现测试用例的 ref_req_id 与其父工作项关系不一致",
                affected_count=len(inconsistent_relationships),
                sample_data=inconsistent_relationships[:self.sample_size],
                suggestions=[
                    "修正测试用例的工作流项父子关系",
                    "确保 ref_req_id 指向的需求存在",
                    "验证工作流项的 parent_item_id 设置正确"
                ]
            )
            self.issues.append(issue)

    def _generate_report(self) -> ConsistencyAuditReport:
        """生成审计报告"""
        issues_by_severity = {}
        for issue in self.issues:
            issues_by_severity[issue.severity] = issues_by_severity.get(issue.severity, 0) + 1

        # 生成总结
        summary = {
            "total_issues": str(len(self.issues)),
            "critical_issues": str(issues_by_severity.get("CRITICAL", 0)),
            "high_issues": str(issues_by_severity.get("HIGH", 0)),
            "medium_issues": str(issues_by_severity.get("MEDIUM", 0)),
            "low_issues": str(issues_by_severity.get("LOW", 0))
        }

        # 生成状态信息
        status_info = "数据一致性审计完成"
        if len(self.issues) == 0:
            status_info = "✅ 所有数据一致性检查通过，未发现问题"
        elif issues_by_severity.get("CRITICAL", 0) > 0:
            status_info = "🚨 发现关键数据一致性问题，需要立即处理"
        elif issues_by_severity.get("HIGH", 0) > 0:
            status_info = "⚠️ 发现高优先级数据一致性问题，建议尽快处理"

        summary["status"] = status_info

        return ConsistencyAuditReport(
            audit_timestamp=datetime.now(timezone.utc),
            total_issues=len(self.issues),
            issues_by_severity=issues_by_severity,
            issues=self.issues,
            summary=summary
        )


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="工作流数据一致性审计工具")
    parser.add_argument(
        "--output", 
        choices=["json", "console"], 
        default="console",
        help="输出格式（json或console）"
    )
    parser.add_argument(
        "--fix-suggestions",
        action="store_true",
        help="包含修复建议"
    )

    args = parser.parse_args()

    try:
        # 创建审计器并执行审计
        auditor = WorkflowConsistencyAuditor()
        report = await auditor.audit_all()

        # 输出结果
        if args.output == "json":
            # JSON格式输出
            output_data = report.model_dump()
            print(json.dumps(output_data, ensure_ascii=False, indent=2))
        else:
            # 控制台格式输出
            print(f"\n{'='*80}")
            print(f"工作流数据一致性审计报告")
            print(f"{'='*80}")
            print(f"审计时间: {report.audit_timestamp}")
            print(f"状态: {report.summary['status']}")
            print(f"\n问题统计:")
            print(f"  总计: {report.total_issues}")
            print(f"  关键: {report.issues_by_severity.get('CRITICAL', 0)}")
            print(f"  高:   {report.issues_by_severity.get('HIGH', 0)}")
            print(f"  中:   {report.issues_by_severity.get('MEDIUM', 0)}")
            print(f"  低:   {report.issues_by_severity.get('LOW', 0)}")

            if report.issues:
                print(f"\n详细问题:")
                for i, issue in enumerate(report.issues, 1):
                    print(f"\n{i}. [{issue.severity}] {issue.title}")
                    print(f"   类型: {issue.issue_type}")
                    print(f"   描述: {issue.description}")
                    print(f"   影响: {issue.affected_count} 个记录")

                    if issue.sample_data:
                        print(f"   样本数据:")
                        for sample in issue.sample_data[:3]:  # 只显示前3个样本
                            print(f"     - {sample}")

                    if args.fix_suggestions and issue.suggestions:
                        print(f"   修复建议:")
                        for suggestion in issue.suggestions:
                            print(f"     - {suggestion}")
            else:
                print(f"\n✅ 未发现数据一致性问题")

            print(f"\n{'='*80}")

    except Exception as e:
        logger.error(f"审计过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())