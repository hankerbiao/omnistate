#!/usr/bin/env python3
"""
工作流一致性审计脚本

该脚本检查以下数据一致性问题：
1. 缺失 workflow_item_id 的业务记录
2. 状态不一致问题 (Requirement.status != WorkItem.current_state)
3. 状态不一致问题 (TestCase.status != WorkItem.current_state)
4. 删除状态不一致 - 业务文档删除但工作流项活跃
5. 删除状态不一致 - 工作流项删除但业务文档活跃
6. 测试用例父子关系不一致 (ref_req_id 与 parent_item_id 不匹配)

使用方法：
python scripts/audit_workflow_consistency.py
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from beanie import PydanticObjectId
from pymongo import AsyncMongoClient

# 导入相关模型
from app.modules.workflow.repository.models.business import BusWorkItemDoc
from app.modules.test_specs.repository.models.requirement import TestRequirementDoc
from app.modules.test_specs.repository.models.test_case import TestCaseDoc


class WorkflowConsistencyAuditor:
    """工作流一致性审计器"""

    def __init__(self):
        self.audit_results = {
            "audit_time": datetime.now().isoformat(),
            "summary": {},
            "details": {}
        }
        self.mongo_client: Optional[AsyncMongoClient] = None

    async def connect_to_mongodb(self):
        """连接到 MongoDB"""
        try:
            # 从环境变量获取 MongoDB 连接信息
            mongo_uri = "mongodb://localhost:27017/dmlv4_backend"
            self.mongo_client = AsyncMongoClient(mongo_uri)
            print(f"✅ 成功连接到 MongoDB: {mongo_uri}")

            # 初始化 Beanie
            from beanie import init_beanie
            await init_beanie(
                database=self.mongo_client.dmlv4_backend,
                document_models=[
                    BusWorkItemDoc,
                    TestRequirementDoc,
                    TestCaseDoc
                ]
            )
            print("✅ 成功初始化 Beanie ODM")

        except Exception as e:
            print(f"❌ 连接 MongoDB 失败: {e}")
            raise

    async def disconnect_from_mongodb(self):
        """断开 MongoDB 连接"""
        if self.mongo_client:
            await self.mongo_client.close()
            print("✅ 已断开 MongoDB 连接")

    async def audit_missing_workflow_item_ids(self) -> Dict[str, Any]:
        """审计缺失 workflow_item_id 的业务记录"""
        print("\n🔍 审计缺失 workflow_item_id 的业务记录...")

        # 检查需求文档
        requirements_without_workflow = await TestRequirementDoc.find(
            {"workflow_item_id": None, "is_deleted": False}
        ).to_list()

        # 检查测试用例文档
        test_cases_without_workflow = await TestCaseDoc.find(
            {"workflow_item_id": None, "is_deleted": False}
        ).to_list()

        result = {
            "description": "检查缺失 workflow_item_id 的业务记录",
            "requirements_without_workflow": [
                {
                    "id": str(req.id),
                    "req_id": req.req_id,
                    "title": req.title,
                    "created_at": req.created_at.isoformat()
                }
                for req in requirements_without_workflow
            ],
            "test_cases_without_workflow": [
                {
                    "id": str(tc.id),
                    "case_id": tc.case_id,
                    "title": tc.title,
                    "ref_req_id": tc.ref_req_id,
                    "created_at": tc.created_at.isoformat()
                }
                for tc in test_cases_without_workflow
            ],
            "total_count": len(requirements_without_workflow) + len(test_cases_without_workflow)
        }

        print(f"   发现 {len(requirements_without_workflow)} 个需求缺失 workflow_item_id")
        print(f"   发现 {len(test_cases_without_workflow)} 个测试用例缺失 workflow_item_id")

        return result

    async def audit_status_inconsistency(self) -> Dict[str, Any]:
        """审计状态不一致问题"""
        print("\n🔍 审计状态不一致问题...")

        # 检查需求状态不一致
        requirements_with_inconsistent_status = []

        # 获取所有需求及其关联的工作流项
        requirements = await TestRequirementDoc.find({"is_deleted": False}).to_list()

        for req in requirements:
            if req.workflow_item_id:
                try:
                    # 转换为 ObjectId
                    workflow_item_id = PydanticObjectId(req.workflow_item_id)
                    work_item = await BusWorkItemDoc.get(workflow_item_id)

                    if work_item and req.status != work_item.current_state:
                        requirements_with_inconsistent_status.append({
                            "requirement_id": str(req.id),
                            "req_id": req.req_id,
                            "requirement_status": req.status,
                            "work_item_id": str(work_item.id),
                            "work_item_state": work_item.current_state,
                            "inconsistency": f"需求状态 '{req.status}' != 工作流状态 '{work_item.current_state}'"
                        })
                except Exception as e:
                    print(f"   ⚠️  无法检查需求 {req.req_id}: {e}")

        # 检查测试用例状态不一致
        test_cases_with_inconsistent_status = []

        test_cases = await TestCaseDoc.find({"is_deleted": False}).to_list()

        for tc in test_cases:
            if tc.workflow_item_id:
                try:
                    # 转换为 ObjectId
                    workflow_item_id = PydanticObjectId(tc.workflow_item_id)
                    work_item = await BusWorkItemDoc.get(workflow_item_id)

                    if work_item and tc.status != work_item.current_state:
                        test_cases_with_inconsistent_status.append({
                            "test_case_id": str(tc.id),
                            "case_id": tc.case_id,
                            "test_case_status": tc.status,
                            "work_item_id": str(work_item.id),
                            "work_item_state": work_item.current_state,
                            "inconsistency": f"用例状态 '{tc.status}' != 工作流状态 '{work_item.current_state}'"
                        })
                except Exception as e:
                    print(f"   ⚠️  无法检查测试用例 {tc.case_id}: {e}")

        result = {
            "description": "检查业务文档状态与工作流状态不一致的问题",
            "requirements_with_inconsistent_status": requirements_with_inconsistent_status,
            "test_cases_with_inconsistent_status": test_cases_with_inconsistent_status,
            "total_count": len(requirements_with_inconsistent_status) + len(test_cases_with_inconsistent_status)
        }

        print(f"   发现 {len(requirements_with_inconsistent_status)} 个需求状态不一致")
        print(f"   发现 {len(test_cases_with_inconsistent_status)} 个测试用例状态不一致")

        return result

    async def audit_delete_inconsistency(self) -> Dict[str, Any]:
        """审计删除状态不一致问题"""
        print("\n🔍 审计删除状态不一致问题...")

        # 检查业务文档删除但工作流项活跃
        business_deleted_workitem_active = []

        # 检查需求
        deleted_requirements = await TestRequirementDoc.find({"is_deleted": True}).to_list()

        for req in deleted_requirements:
            if req.workflow_item_id:
                try:
                    workflow_item_id = PydanticObjectId(req.workflow_item_id)
                    work_item = await BusWorkItemDoc.get(workflow_item_id)

                    if work_item and not work_item.is_deleted:
                        business_deleted_workitem_active.append({
                            "business_doc_type": "requirement",
                            "business_doc_id": str(req.id),
                            "business_doc_identifier": req.req_id,
                            "work_item_id": str(work_item.id),
                            "work_item_title": work_item.title,
                            "inconsistency": f"需求已删除但工作流项仍活跃"
                        })
                except Exception as e:
                    print(f"   ⚠️  无法检查已删除需求 {req.req_id}: {e}")

        # 检查测试用例
        deleted_test_cases = await TestCaseDoc.find({"is_deleted": True}).to_list()

        for tc in deleted_test_cases:
            if tc.workflow_item_id:
                try:
                    workflow_item_id = PydanticObjectId(tc.workflow_item_id)
                    work_item = await BusWorkItemDoc.get(workflow_item_id)

                    if work_item and not work_item.is_deleted:
                        business_deleted_workitem_active.append({
                            "business_doc_type": "test_case",
                            "business_doc_id": str(tc.id),
                            "business_doc_identifier": tc.case_id,
                            "work_item_id": str(work_item.id),
                            "work_item_title": work_item.title,
                            "inconsistency": f"测试用例已删除但工作流项仍活跃"
                        })
                except Exception as e:
                    print(f"   ⚠️  无法检查已删除测试用例 {tc.case_id}: {e}")

        # 检查工作流项删除但业务文档活跃
        workitem_deleted_business_active = []

        deleted_work_items = await BusWorkItemDoc.find({"is_deleted": True}).to_list()

        for work_item in deleted_work_items:
            # 检查关联的需求
            if work_item.type_code in ["REQUIREMENT"]:
                req = await TestRequirementDoc.find_one(
                    {"workflow_item_id": str(work_item.id), "is_deleted": False}
                )
                if req:
                    workitem_deleted_business_active.append({
                        "work_item_id": str(work_item.id),
                        "work_item_title": work_item.title,
                        "work_item_type": work_item.type_code,
                        "business_doc_type": "requirement",
                        "business_doc_id": str(req.id),
                        "business_doc_identifier": req.req_id,
                        "inconsistency": f"工作流项已删除但需求仍活跃"
                    })

            # 检查关联的测试用例
            elif work_item.type_code in ["TEST_CASE"]:
                tc = await TestCaseDoc.find_one(
                    {"workflow_item_id": str(work_item.id), "is_deleted": False}
                )
                if tc:
                    workitem_deleted_business_active.append({
                        "work_item_id": str(work_item.id),
                        "work_item_title": work_item.title,
                        "work_item_type": work_item.type_code,
                        "business_doc_type": "test_case",
                        "business_doc_id": str(tc.id),
                        "business_doc_identifier": tc.case_id,
                        "inconsistency": f"工作流项已删除但测试用例仍活跃"
                    })

        result = {
            "description": "检查删除状态不一致的问题",
            "business_deleted_workitem_active": business_deleted_workitem_active,
            "workitem_deleted_business_active": workitem_deleted_business_active,
            "total_count": len(business_deleted_workitem_active) + len(workitem_deleted_business_active)
        }

        print(f"   发现 {len(business_deleted_workitem_active)} 个业务文档删除但工作流项活跃的记录")
        print(f"   发现 {len(workitem_deleted_business_active)} 个工作流项删除但业务文档活跃的记录")

        return result

    async def audit_parent_child_inconsistency(self) -> Dict[str, Any]:
        """审计父子关系不一致问题"""
        print("\n🔍 审计父子关系不一致问题...")

        inconsistent_parent_child_relations = []

        # 检查测试用例的 ref_req_id 与父工作流项的 parent_item_id 是否匹配
        test_cases = await TestCaseDoc.find({"is_deleted": False}).to_list()

        for tc in test_cases:
            if tc.workflow_item_id and tc.ref_req_id:
                try:
                    # 获取测试用例的工作流项
                    workflow_item_id = PydanticObjectId(tc.workflow_item_id)
                    tc_work_item = await BusWorkItemDoc.get(workflow_item_id)

                    if tc_work_item:
                        # 获取需求文档
                        req = await TestRequirementDoc.find_one(
                            {"req_id": tc.ref_req_id, "is_deleted": False}
                        )

                        if req and req.workflow_item_id:
                            # 检查父工作流项的 ID 是否匹配
                            parent_work_item_id = tc_work_item.parent_item_id
                            if parent_work_item_id and req.workflow_item_id:
                                if parent_work_item_id != req.workflow_item_id:
                                    inconsistent_parent_child_relations.append({
                                        "test_case_id": str(tc.id),
                                        "test_case_identifier": tc.case_id,
                                        "test_case_work_item_id": str(tc_work_item.id),
                                        "referenced_req_id": tc.ref_req_id,
                                        "req_work_item_id": req.workflow_item_id,
                                        "tc_parent_item_id": str(parent_work_item_id) if parent_work_item_id else None,
                                        "inconsistency": f"测试用例引用需求 {tc.ref_req_id}，但父工作流项不匹配"
                                    })
                except Exception as e:
                    print(f"   ⚠️  无法检查测试用例 {tc.case_id} 的父子关系: {e}")

        result = {
            "description": "检查父子关系不一致的问题",
            "inconsistent_parent_child_relations": inconsistent_parent_child_relations,
            "total_count": len(inconsistent_parent_child_relations)
        }

        print(f"   发现 {len(inconsistent_parent_child_relations)} 个父子关系不一致的记录")

        return result

    async def run_full_audit(self) -> Dict[str, Any]:
        """运行完整的审计流程"""
        print("🚀 开始工作流一致性审计...")

        try:
            await self.connect_to_mongodb()

            # 执行各项审计
            self.audit_results["details"]["missing_workflow_item_ids"] = await self.audit_missing_workflow_item_ids()
            self.audit_results["details"]["status_inconsistency"] = await self.audit_status_inconsistency()
            self.audit_results["details"]["delete_inconsistency"] = await self.audit_delete_inconsistency()
            self.audit_results["details"]["parent_child_inconsistency"] = await self.audit_parent_child_inconsistency()

            # 生成总结
            self.audit_results["summary"] = {
                "missing_workflow_item_ids": self.audit_results["details"]["missing_workflow_item_ids"]["total_count"],
                "status_inconsistency": self.audit_results["details"]["status_inconsistency"]["total_count"],
                "delete_inconsistency": self.audit_results["details"]["delete_inconsistency"]["total_count"],
                "parent_child_inconsistency": self.audit_results["details"]["parent_child_inconsistency"]["total_count"],
                "total_inconsistencies": sum([
                    self.audit_results["details"]["missing_workflow_item_ids"]["total_count"],
                    self.audit_results["details"]["status_inconsistency"]["total_count"],
                    self.audit_results["details"]["delete_inconsistency"]["total_count"],
                    self.audit_results["details"]["parent_child_inconsistency"]["total_count"]
                ])
            }

            print(f"\n✅ 审计完成！发现总计 {self.audit_results['summary']['total_inconsistencies']} 个不一致问题")

        except Exception as e:
            print(f"❌ 审计失败: {e}")
            raise
        finally:
            await self.disconnect_from_mongodb()

        return self.audit_results

    def save_audit_report(self, output_file: str = None):
        """保存审计报告"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"audit_workflow_consistency_{timestamp}.json"

        output_path = Path(output_file)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.audit_results, f, indent=2, ensure_ascii=False)

        print(f"📄 审计报告已保存到: {output_path}")

        return str(output_path)


async def main():
    """主函数"""
    auditor = WorkflowConsistencyAuditor()

    try:
        # 运行审计
        await auditor.run_full_audit()

        # 保存报告
        report_file = auditor.save_audit_report()

        # 输出摘要
        print("\n📊 审计摘要:")
        summary = auditor.audit_results["summary"]
        print(f"   缺失 workflow_item_id: {summary['missing_workflow_item_ids']} 个")
        print(f"   状态不一致: {summary['status_inconsistency']} 个")
        print(f"   删除状态不一致: {summary['delete_inconsistency']} 个")
        print(f"   父子关系不一致: {summary['parent_child_inconsistency']} 个")
        print(f"   总计: {summary['total_inconsistencies']} 个")

        return report_file

    except Exception as e:
        print(f"❌ 审计过程失败: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(main())