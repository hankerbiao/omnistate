#!/usr/bin/env python3
"""
数据一致性修复脚本 - Phase 7

此脚本修复工作流系统的数据一致性，能够处理以下6种不一致性：

1. 缺少 workflow_item_id 的业务记录
2. Requirement.status != WorkItem.current_state
3. TestCase.status != WorkItem.current_state
4. 业务文档被删除但工作项仍活跃
5. 工作项被删除但业务文档仍活跃
6. 测试用例的 ref_req_id 和父工作项关系不一致

Usage:
    python scripts/repair_workflow_consistency.py --dry-run
    python scripts/repair_workflow_consistency.py --fix-missing-ids
    python scripts/repair_workflow_consistency.py --sync-statuses
    python scripts/repair_workflow_consistency.py --cleanup-orphans
    python scripts/repair_workflow_consistency.py --fix-relationships
    python scripts/repair_workflow_consistency.py --all
"""

import asyncio
import argparse
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set
from pydantic import BaseModel
from beanie import PydanticObjectId

from app.modules.workflow.repository.models.business import BusWorkItemDoc
from app.modules.test_specs.repository.models.requirement import TestRequirementDoc
from app.modules.test_specs.repository.models.test_case import TestCaseDoc
from app.shared.core.logger import log as logger


class RepairOperation(BaseModel):
    """修复操作的数据模型"""
    operation_type: str
    description: str
    target_count: int
    success_count: int = 0
    failed_count: int = 0
    details: List[str] = []


class RepairResult(BaseModel):
    """修复结果的数据模型"""
    repair_timestamp: datetime
    total_operations: int
    total_processed: int
    total_succeeded: int
    total_failed: int
    operations: List[RepairOperation]
    summary: Dict[str, str]


class WorkflowConsistencyRepairer:
    """工作流一致性修复器"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.operations: List[RepairOperation] = []
        self.processed_count = 0
        self.succeeded_count = 0
        self.failed_count = 0

    async def repair_all(self, audit_report_path: Optional[str] = None) -> RepairResult:
        """执行所有修复操作"""
        if self.dry_run:
            logger.info("执行修复操作（dry-run模式）")
        else:
            logger.info("开始执行数据一致性修复...")

        # 如果提供了审计报告，从报告读取问题
        if audit_report_path:
            await self._repair_from_audit_report(audit_report_path)
        else:
            # 依次执行各种修复操作
            await self._repair_missing_workflow_item_ids()
            await self._sync_requirement_statuses()
            await self._sync_test_case_statuses()
            await self._cleanup_deleted_business_orphans()
            await self._cleanup_deleted_work_item_orphans()
            await self._fix_test_case_requirement_relationships()

        # 生成结果报告
        result = self._generate_result()
        logger.info(f"数据一致性修复完成，处理 {result.total_processed} 个记录，成功 {result.total_succeeded} 个，失败 {result.total_failed} 个")

        return result

    async def _repair_from_audit_report(self, audit_report_path: str):
        """从审计报告执行修复"""
        logger.info(f"从审计报告执行修复: {audit_report_path}")

        with open(audit_report_path, 'r', encoding='utf-8') as f:
            audit_data = json.load(f)

        # 根据问题类型执行对应的修复操作
        for issue in audit_data.get('issues', []):
            issue_type = issue['issue_type']

            if issue_type == 'missing_workflow_item_id':
                await self._repair_missing_workflow_item_ids_from_samples(issue.get('sample_data', []))
            elif issue_type == 'requirement_status_inconsistency':
                await self._sync_requirement_statuses_from_samples(issue.get('sample_data', []))
            elif issue_type == 'test_case_status_inconsistency':
                await self._sync_test_case_statuses_from_samples(issue.get('sample_data', []))
            elif issue_type == 'deleted_business_active_work_items':
                await self._cleanup_deleted_business_orphans_from_samples(issue.get('sample_data', []))
            elif issue_type == 'deleted_work_items_active_business':
                await self._cleanup_deleted_work_item_orphans_from_samples(issue.get('sample_data', []))
            elif issue_type == 'test_case_requirement_relationship_inconsistency':
                await self._fix_test_case_requirement_relationships_from_samples(issue.get('sample_data', []))

    async def _create_operation(self, operation_type: str, description: str, target_count: int) -> RepairOperation:
        """创建修复操作记录"""
        operation = RepairOperation(
            operation_type=operation_type,
            description=description,
            target_count=target_count
        )
        self.operations.append(operation)
        return operation

    async def _update_operation_result(self, operation: RepairOperation, success: bool, detail: str = ""):
        """更新操作结果"""
        self.processed_count += 1

        if success:
            operation.success_count += 1
            self.succeeded_count += 1
        else:
            operation.failed_count += 1
            self.failed_count += 1

        if detail:
            operation.details.append(detail)

    async def _repair_missing_workflow_item_ids(self):
        """修复缺少 workflow_item_id 的业务记录"""
        operation = await self._create_operation(
            "repair_missing_workflow_item_ids",
            "修复缺少 workflow_item_id 的业务记录",
            0
        )

        # 处理需求
        requirements = await TestRequirementDoc.find({"workflow_item_id": None, "is_deleted": False}).to_list()
        operation.target_count += len(requirements)

        for req in requirements:
            try:
                # 创建对应的工作流项
                work_item = BusWorkItemDoc(
                    type_code="REQUIREMENT",
                    title=f"需求项: {req.title}",
                    content=req.description or "",
                    parent_item_id=None,
                    current_state="DRAFT",
                    current_owner_id=req.tpm_owner_id,
                    creator_id=req.tpm_owner_id
                )

                if not self.dry_run:
                    await work_item.insert()
                    # 更新需求的 workflow_item_id
                    req.workflow_item_id = str(work_item.id)
                    await req.save()

                await self._update_operation_result(operation, True, f"为需求 {req.req_id} 创建工作流项")
            except Exception as e:
                await self._update_operation_result(operation, False, f"修复需求 {req.req_id} 失败: {str(e)}")

        # 处理测试用例
        test_cases = await TestCaseDoc.find({"workflow_item_id": None, "is_deleted": False}).to_list()
        operation.target_count += len(test_cases)

        for tc in test_cases:
            try:
                # 创建对应的工作流项
                work_item = BusWorkItemDoc(
                    type_code="TEST_CASE",
                    title=f"测试用例: {tc.title}",
                    content="",
                    parent_item_id=None,
                    current_state="DRAFT",
                    current_owner_id=tc.owner_id or "",
                    creator_id=tc.owner_id or ""
                )

                if not self.dry_run:
                    await work_item.insert()
                    # 更新测试用例的 workflow_item_id
                    tc.workflow_item_id = str(work_item.id)
                    await tc.save()

                await self._update_operation_result(operation, True, f"为测试用例 {tc.case_id} 创建工作流项")
            except Exception as e:
                await self._update_operation_result(operation, False, f"修复测试用例 {tc.case_id} 失败: {str(e)}")

    async def _repair_missing_workflow_item_ids_from_samples(self, samples: List[Dict[str, Any]]):
        """从样本数据修复缺少 workflow_item_id 的问题"""
        operation = await self._create_operation(
            "repair_missing_workflow_item_ids",
            "从样本数据修复缺少 workflow_item_id 的业务记录",
            len(samples)
        )

        for sample in samples:
            try:
                if sample['type'] == 'requirement':
                    req = await TestRequirementDoc.get(sample['id'])
                    if req and req.workflow_item_id is None:
                        work_item = BusWorkItemDoc(
                            type_code="REQUIREMENT",
                            title=f"需求项: {req.title}",
                            content=req.description or "",
                            current_state="DRAFT",
                            current_owner_id=req.tpm_owner_id,
                            creator_id=req.tpm_owner_id
                        )

                        if not self.dry_run:
                            await work_item.insert()
                            req.workflow_item_id = str(work_item.id)
                            await req.save()

                        await self._update_operation_result(operation, True, f"修复需求 {req.req_id}")
                    else:
                        await self._update_operation_result(operation, True, f"需求 {req.req_id} 已修复或不需要修复")

                elif sample['type'] == 'test_case':
                    tc = await TestCaseDoc.get(sample['id'])
                    if tc and tc.workflow_item_id is None:
                        work_item = BusWorkItemDoc(
                            type_code="TEST_CASE",
                            title=f"测试用例: {tc.title}",
                            content="",
                            current_state="DRAFT",
                            current_owner_id=tc.owner_id or "",
                            creator_id=tc.owner_id or ""
                        )

                        if not self.dry_run:
                            await work_item.insert()
                            tc.workflow_item_id = str(work_item.id)
                            await tc.save()

                        await self._update_operation_result(operation, True, f"修复测试用例 {tc.case_id}")
                    else:
                        await self._update_operation_result(operation, True, f"测试用例 {tc.case_id} 已修复或不需要修复")

            except Exception as e:
                await self._update_operation_result(operation, False, f"修复失败: {str(e)}")

    async def _sync_requirement_statuses(self):
        """同步需求状态到工作流状态"""
        operation = await self._create_operation(
            "sync_requirement_statuses",
            "同步需求状态到工作流状态",
            0
        )

        # 获取所有非删除的需求及其工作流项
        requirements = await TestRequirementDoc.find({"is_deleted": False}).to_list()
        operation.target_count = len(requirements)

        for req in requirements:
            if req.workflow_item_id:
                try:
                    work_item = await BusWorkItemDoc.get(req.workflow_item_id)
                    if work_item and req.status != work_item.current_state:
                        if not self.dry_run:
                            # 同步状态
                            req.status = work_item.current_state
                            await req.save()

                        await self._update_operation_result(
                            operation, True, 
                            f"同步需求 {req.req_id} 状态从 {req.status} 到 {work_item.current_state}"
                        )
                    else:
                        await self._update_operation_result(operation, True, f"需求 {req.req_id} 状态已一致")
                except Exception as e:
                    await self._update_operation_result(operation, False, f"同步需求 {req.req_id} 失败: {str(e)}")
            else:
                await self._update_operation_result(operation, False, f"需求 {req.req_id} 缺少工作流ID")

    async def _sync_requirement_statuses_from_samples(self, samples: List[Dict[str, Any]]):
        """从样本数据同步需求状态"""
        operation = await self._create_operation(
            "sync_requirement_statuses",
            "从样本数据同步需求状态",
            len(samples)
        )

        for sample in samples:
            try:
                req = await TestRequirementDoc.get(sample['requirement_id'])
                if req:
                    if not self.dry_run:
                        req.status = sample['work_item_state']
                        await req.save()

                    await self._update_operation_result(operation, True, f"同步需求 {req.req_id}")
                else:
                    await self._update_operation_result(operation, False, f"需求 {sample['requirement_id']} 不存在")

            except Exception as e:
                await self._update_operation_result(operation, False, f"同步需求状态失败: {str(e)}")

    async def _sync_test_case_statuses(self):
        """同步测试用例状态到工作流状态"""
        operation = await self._create_operation(
            "sync_test_case_statuses",
            "同步测试用例状态到工作流状态",
            0
        )

        # 获取所有非删除的测试用例及其工作流项
        test_cases = await TestCaseDoc.find({"is_deleted": False}).to_list()
        operation.target_count = len(test_cases)

        for tc in test_cases:
            if tc.workflow_item_id:
                try:
                    work_item = await BusWorkItemDoc.get(tc.workflow_item_id)
                    if work_item and tc.status != work_item.current_state:
                        if not self.dry_run:
                            # 同步状态
                            tc.status = work_item.current_state
                            await tc.save()

                        await self._update_operation_result(
                            operation, True, 
                            f"同步测试用例 {tc.case_id} 状态从 {tc.status} 到 {work_item.current_state}"
                        )
                    else:
                        await self._update_operation_result(operation, True, f"测试用例 {tc.case_id} 状态已一致")
                except Exception as e:
                    await self._update_operation_result(operation, False, f"同步测试用例 {tc.case_id} 失败: {str(e)}")
            else:
                await self._update_operation_result(operation, False, f"测试用例 {tc.case_id} 缺少工作流ID")

    async def _sync_test_case_statuses_from_samples(self, samples: List[Dict[str, Any]]):
        """从样本数据同步测试用例状态"""
        operation = await self._create_operation(
            "sync_test_case_statuses",
            "从样本数据同步测试用例状态",
            len(samples)
        )

        for sample in samples:
            try:
                tc = await TestCaseDoc.get(sample['test_case_id'])
                if tc:
                    if not self.dry_run:
                        tc.status = sample['work_item_state']
                        await tc.save()

                    await self._update_operation_result(operation, True, f"同步测试用例 {tc.case_id}")
                else:
                    await self._update_operation_result(operation, False, f"测试用例 {sample['test_case_id']} 不存在")

            except Exception as e:
                await self._update_operation_result(operation, False, f"同步测试用例状态失败: {str(e)}")

    async def _cleanup_deleted_business_orphans(self):
        """清理业务文档被删除但工作项仍活跃的孤立记录"""
        operation = await self._create_operation(
            "cleanup_deleted_business_orphans",
            "清理业务文档被删除但工作项仍活跃的孤立记录",
            0
        )

        # 获取所有被删除的需求对应的活跃工作项
        deleted_requirements = await TestRequirementDoc.find({"is_deleted": True}).to_list()
        deleted_work_items = set()

        for req in deleted_requirements:
            if req.workflow_item_id:
                try:
                    work_item = await BusWorkItemDoc.get(req.workflow_item_id)
                    if work_item and not work_item.is_deleted:
                        deleted_work_items.add(str(work_item.id))

                        if not self.dry_run:
                            work_item.is_deleted = True
                            await work_item.save()

                        await self._update_operation_result(operation, True, f"删除需求 {req.req_id} 对应的孤立工作项")
                except Exception as e:
                    await self._update_operation_result(operation, False, f"处理需求 {req.req_id} 对应工作项失败: {str(e)}")

        # 获取所有被删除的测试用例对应的活跃工作项
        deleted_test_cases = await TestCaseDoc.find({"is_deleted": True}).to_list()

        for tc in deleted_test_cases:
            if tc.workflow_item_id:
                try:
                    work_item = await BusWorkItemDoc.get(tc.workflow_item_id)
                    if work_item and not work_item.is_deleted:
                        if str(work_item.id) not in deleted_work_items:  # 避免重复删除
                            if not self.dry_run:
                                work_item.is_deleted = True
                                await work_item.save()

                            await self._update_operation_result(operation, True, f"删除测试用例 {tc.case_id} 对应的孤立工作项")
                except Exception as e:
                    await self._update_operation_result(operation, False, f"处理测试用例 {tc.case_id} 对应工作项失败: {str(e)}")

        operation.target_count = self.processed_count

    async def _cleanup_deleted_business_orphans_from_samples(self, samples: List[Dict[str, Any]]):
        """从样本数据清理业务文档孤立记录"""
        operation = await self._create_operation(
            "cleanup_deleted_business_orphans",
            "从样本数据清理业务文档孤立记录",
            len(samples)
        )

        for sample in samples:
            try:
                work_item = await BusWorkItemDoc.get(sample['work_item_id'])
                if work_item and not work_item.is_deleted:
                    if not self.dry_run:
                        work_item.is_deleted = True
                        await work_item.save()

                    await self._update_operation_result(operation, True, f"删除孤立工作项 {work_item.title}")
                else:
                    await self._update_operation_result(operation, True, f"工作项 {sample['work_item_id']} 不需要删除")

            except Exception as e:
                await self._update_operation_result(operation, False, f"清理孤立工作项失败: {str(e)}")

    async def _cleanup_deleted_work_item_orphans(self):
        """清理工作项被删除但业务文档仍活跃的孤立记录"""
        operation = await self._create_operation(
            "cleanup_deleted_work_item_orphans",
            "清理工作项被删除但业务文档仍活跃的孤立记录",
            0
        )

        # 获取所有已删除的工作项
        deleted_work_items = await BusWorkItemDoc.find({"is_deleted": True}).to_list()

        for work_item in deleted_work_items:
            # 查找关联的活跃需求
            requirements = await TestRequirementDoc.find(
                {"workflow_item_id": str(work_item.id), "is_deleted": False}
            ).to_list()

            for req in requirements:
                if not self.dry_run:
                    req.is_deleted = True
                    await req.save()

                await self._update_operation_result(operation, True, f"删除孤立需求 {req.req_id}")

            # 查找关联的活跃测试用例
            test_cases = await TestCaseDoc.find(
                {"workflow_item_id": str(work_item.id), "is_deleted": False}
            ).to_list()

            for tc in test_cases:
                if not self.dry_run:
                    tc.is_deleted = True
                    await tc.save()

                await self._update_operation_result(operation, True, f"删除孤立测试用例 {tc.case_id}")

        operation.target_count = self.processed_count

    async def _cleanup_deleted_work_item_orphans_from_samples(self, samples: List[Dict[str, Any]]):
        """从样本数据清理工作项孤立记录"""
        operation = await self._create_operation(
            "cleanup_deleted_work_item_orphans",
            "从样本数据清理工作项孤立记录",
            len(samples)
        )

        processed_business_ids = set()

        for sample in samples:
            business_id = sample['business_id']
            if business_id in processed_business_ids:
                continue  # 避免重复处理

            processed_business_ids.add(business_id)

            try:
                if sample['business_type'] == 'requirement':
                    req = await TestRequirementDoc.get(business_id)
                    if req and not req.is_deleted:
                        if not self.dry_run:
                            req.is_deleted = True
                            await req.save()

                        await self._update_operation_result(operation, True, f"删除孤立需求 {req.req_id}")
                    else:
                        await self._update_operation_result(operation, True, f"需求 {business_id} 不需要删除")

                elif sample['business_type'] == 'test_case':
                    tc = await TestCaseDoc.get(business_id)
                    if tc and not tc.is_deleted:
                        if not self.dry_run:
                            tc.is_deleted = True
                            await tc.save()

                        await self._update_operation_result(operation, True, f"删除孤立测试用例 {tc.case_id}")
                    else:
                        await self._update_operation_result(operation, True, f"测试用例 {business_id} 不需要删除")

            except Exception as e:
                await self._update_operation_result(operation, False, f"清理孤立记录失败: {str(e)}")

    async def _fix_test_case_requirement_relationships(self):
        """修复测试用例与需求的关联关系"""
        operation = await self._create_operation(
            "fix_test_case_requirement_relationships",
            "修复测试用例与需求的关联关系",
            0
        )

        test_cases = await TestCaseDoc.find({"is_deleted": False}).to_list()
        operation.target_count = len(test_cases)

        for tc in test_cases:
            try:
                # 查找对应的需求
                requirement = await TestRequirementDoc.find_one(
                    {"req_id": tc.ref_req_id, "is_deleted": False}
                )

                if requirement and requirement.workflow_item_id and tc.workflow_item_id:
                    # 检查并修复父子关系
                    tc_work_item = await BusWorkItemDoc.get(tc.workflow_item_id)
                    if tc_work_item and tc_work_item.parent_item_id != requirement.workflow_item_id:
                        if not self.dry_run:
                            tc_work_item.parent_item_id = requirement.workflow_item_id
                            await tc_work_item.save()

                        await self._update_operation_result(
                            operation, True, 
                            f"修复测试用例 {tc.case_id} 的父子关系"
                        )
                    else:
                        await self._update_operation_result(operation, True, f"测试用例 {tc.case_id} 关系正确")

                elif not requirement:
                    await self._update_operation_result(operation, False, f"测试用例 {tc.case_id} 引用的需求不存在")
                elif not requirement.workflow_item_id:
                    await self._update_operation_result(operation, False, f"需求 {requirement.req_id} 缺少工作流ID")
                elif not tc.workflow_item_id:
                    await self._update_operation_result(operation, False, f"测试用例 {tc.case_id} 缺少工作流ID")

            except Exception as e:
                await self._update_operation_result(operation, False, f"修复测试用例 {tc.case_id} 关系失败: {str(e)}")

    async def _fix_test_case_requirement_relationships_from_samples(self, samples: List[Dict[str, Any]]):
        """从样本数据修复测试用例与需求的关联关系"""
        operation = await self._create_operation(
            "fix_test_case_requirement_relationships",
            "从样本数据修复测试用例与需求的关联关系",
            len(samples)
        )

        for sample in samples:
            try:
                tc = await TestCaseDoc.get(sample['test_case_id'])
                if tc and tc.workflow_item_id:
                    tc_work_item = await BusWorkItemDoc.get(tc.workflow_item_id)
                    if tc_work_item:
                        if not self.dry_run:
                            tc_work_item.parent_item_id = sample['expected_parent']
                            await tc_work_item.save()

                        await self._update_operation_result(operation, True, f"修复测试用例 {tc.case_id}")
                    else:
                        await self._update_operation_result(operation, False, f"工作流项 {tc.workflow_item_id} 不存在")
                else:
                    await self._update_operation_result(operation, False, f"测试用例 {sample['test_case_id']} 缺少工作流ID")

            except Exception as e:
                await self._update_operation_result(operation, False, f"修复关系失败: {str(e)}")

    def _generate_result(self) -> RepairResult:
        """生成修复结果报告"""
        summary = {
            "dry_run": str(self.dry_run),
            "total_operations": str(len(self.operations)),
            "total_processed": str(self.processed_count),
            "total_succeeded": str(self.succeeded_count),
            "total_failed": str(self.failed_count),
            "success_rate": f"{(self.succeeded_count / max(self.processed_count, 1) * 100):.1f}%"
        }

        if self.failed_count == 0:
            summary["status"] = "✅ 所有修复操作成功完成"
        elif self.succeeded_count > self.failed_count:
            summary["status"] = "⚠️ 大部分修复操作成功，但存在部分失败"
        else:
            summary["status"] = "🚨 修复操作存在较多失败，需要进一步检查"

        return RepairResult(
            repair_timestamp=datetime.now(timezone.utc),
            total_operations=len(self.operations),
            total_processed=self.processed_count,
            total_succeeded=self.succeeded_count,
            total_failed=self.failed_count,
            operations=self.operations,
            summary=summary
        )


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="工作流数据一致性修复工具")
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="预览模式，不实际执行修改"
    )
    parser.add_argument(
        "--fix-missing-ids",
        action="store_true",
        help="修复缺少 workflow_item_id 的记录"
    )
    parser.add_argument(
        "--sync-statuses",
        action="store_true",
        help="同步状态到工作流状态"
    )
    parser.add_argument(
        "--cleanup-orphans",
        action="store_true",
        help="清理孤立记录"
    )
    parser.add_argument(
        "--fix-relationships",
        action="store_true",
        help="修复关联关系"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="执行所有修复操作"
    )
    parser.add_argument(
        "--audit-report",
        type=str,
        help="从审计报告执行修复"
    )

    args = parser.parse_args()

    # 创建修复器
    repairer = WorkflowConsistencyRepairer(dry_run=args.dry_run)

    try:
        # 确定要执行的修复操作
        if args.all:
            # 执行所有修复
            result = await repairer.repair_all()
        elif args.audit_report:
            # 从审计报告执行修复
            result = await repairer.repair_all(audit_report_path=args.audit_report)
        else:
            # 执行特定的修复操作
            operations = []

            if args.fix_missing_ids:
                await repairer._repair_missing_workflow_item_ids()
                operations.append("修复缺少的workflow_item_id")

            if args.sync_statuses:
                await repairer._sync_requirement_statuses()
                await repairer._sync_test_case_statuses()
                operations.append("同步状态")

            if args.cleanup_orphans:
                await repairer._cleanup_deleted_business_orphans()
                await repairer._cleanup_deleted_work_item_orphans()
                operations.append("清理孤立记录")

            if args.fix_relationships:
                await repairer._fix_test_case_requirement_relationships()
                operations.append("修复关联关系")

            if not operations:
                print("请指定要执行的修复操作，或使用 --all 执行所有修复")
                return

            result = repairer._generate_result()
            result.summary["operations_executed"] = ", ".join(operations)

        # 输出结果
        print(f"\n{'='*80}")
        print(f"工作流数据一致性修复报告")
        print(f"{'='*80}")
        print(f"修复时间: {result.repair_timestamp}")
        print(f"模式: {'预览模式（dry-run）' if args.dry_run else '实际执行模式'}")
        print(f"状态: {result.summary['status']}")
        print(f"\n总体统计:")
        print(f"  总操作: {result.total_operations}")
        print(f"  总处理: {result.total_processed}")
        print(f"  成功: {result.total_succeeded}")
        print(f"  失败: {result.total_failed}")
        print(f"  成功率: {result.summary['success_rate']}")

        if result.operations:
            print(f"\n详细操作:")
            for i, op in enumerate(result.operations, 1):
                print(f"\n{i}. {op.description}")
                print(f"   目标: {op.target_count}")
                print(f"   成功: {op.success_count}")
                print(f"   失败: {op.failed_count}")
                if op.details:
                    print(f"   详情: {', '.join(op.details[:3])}")
                    if len(op.details) > 3:
                        print(f"          ... 还有 {len(op.details) - 3} 条详情")

        print(f"\n{'='*80}")

        # 如果是dry-run模式，提示用户
        if args.dry_run:
            print("⚠️ 这是预览模式，未实际执行修改。要执行实际修改，请去掉 --dry-run 参数")

    except Exception as e:
        logger.error(f"修复过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())