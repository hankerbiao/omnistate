#!/usr/bin/env python3
"""
工作流一致性修复脚本

该脚本基于审计结果修复发现的数据一致性问题：
1. 为缺失 workflow_item_id 的业务记录创建对应的工作流项
2. 修复状态不一致问题（同步业务文档状态到工作流状态）
3. 修复删除状态不一致问题（保持删除状态同步）
4. 修复父子关系不一致问题（正确建立工作流项的父子关系）

使用方法：
python scripts/repair_workflow_consistency.py --audit-file audit_workflow_consistency_YYYYMMDD_HHMMSS.json --dry-run
python scripts/repair_workflow_consistency.py --audit-file audit_workflow_consistency_YYYYMMDD_HHMMSS.json --fix-missing-workflow
python scripts/repair_workflow_consistency.py --audit-file audit_workflow_consistency_YYYYMMDD_HHMMSS.json --fix-status
python scripts/repair_workflow_consistency.py --audit-file audit_workflow_consistency_YYYYMMDD_HHMMSS.json --fix-delete
python scripts/repair_workflow_consistency.py --audit-file audit_workflow_consistency_YYYYMMDD_HHMMSS.json --fix-parent-child
python scripts/repair_workflow_consistency.py --audit-file audit_workflow_consistency_YYYYMMDD_HHMMSS.json --fix-all

参数说明：
--dry-run: 仅显示将要执行的修复操作，不实际执行
--audit-file: 指定审计结果文件路径
--fix-missing-workflow: 修复缺失 workflow_item_id 的问题
--fix-status: 修复状态不一致问题
--fix-delete: 修复删除状态不一致问题
--fix-parent-child: 修复父子关系不一致问题
--fix-all: 执行所有修复操作
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from beanie import PydanticObjectId
from pymongo import AsyncMongoClient

# 导入相关模型
from app.modules.workflow.repository.models.business import BusWorkItemDoc
from app.modules.test_specs.repository.models.requirement import TestRequirementDoc
from app.modules.test_specs.repository.models.test_case import TestCaseDoc


class WorkflowConsistencyRepairer:
    """工作流一致性修复器"""

    def __init__(self, audit_results: Dict[str, Any], dry_run: bool = False):
        self.audit_results = audit_results
        self.dry_run = dry_run
        self.repair_results = {
            "repair_time": datetime.now().isoformat(),
            "dry_run": dry_run,
            "summary": {},
            "details": {}
        }
        self.mongo_client: Optional[AsyncMongoClient] = None

    async def connect_to_mongodb(self):
        """连接到 MongoDB"""
        if self.dry_run:
            print("🔍 模式：Dry Run，不会实际连接数据库")
            return

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

    async def repair_missing_workflow_item_ids(self) -> Dict[str, Any]:
        """修复缺失 workflow_item_id 的业务记录"""
        print("\n🔧 修复缺失 workflow_item_id 的业务记录...")

        result = {
            "description": "为缺失 workflow_item_id 的业务记录创建对应的工作流项",
            "requirements_repaired": 0,
            "test_cases_repaired": 0,
            "details": []
        }

        # 修复需求文档
        requirements_without_workflow = self.audit_results["details"]["missing_workflow_item_ids"]["requirements_without_workflow"]
        for req_data in requirements_without_workflow:
            if not self.dry_run:
                try:
                    # 创建对应的工作流项
                    work_item = BusWorkItemDoc(
                        type_code="REQUIREMENT",
                        title=f"[需求] {req_data['title']}",
                        content=f"自动创建的需求工作流项 - {req_data['req_id']}",
                        creator_id="system_repair",  # 使用系统标识
                        current_state="待指派",  # 默认状态
                        current_owner_id=None
                    )

                    # 保存工作流项
                    await work_item.insert()

                    # 更新需求文档的 workflow_item_id
                    req_doc = await TestRequirementDoc.get(PydanticObjectId(req_data["id"]))
                    if req_doc:
                        req_doc.workflow_item_id = str(work_item.id)
                        await req_doc.save()

                    result["requirements_repaired"] += 1
                    result["details"].append({
                        "type": "requirement",
                        "req_id": req_data["req_id"],
                        "work_item_id": str(work_item.id),
                        "status": "success"
                    })

                    print(f"   ✅ 已为需求 {req_data['req_id']} 创建工作流项 {str(work_item.id)}")

                except Exception as e:
                    result["details"].append({
                        "type": "requirement",
                        "req_id": req_data["req_id"],
                        "status": "failed",
                        "error": str(e)
                    })
                    print(f"   ❌ 修复需求 {req_data['req_id']} 失败: {e}")
            else:
                result["requirements_repaired"] += 1
                result["details"].append({
                    "type": "requirement",
                    "req_id": req_data["req_id"],
                    "action": "创建工作流项并更新 workflow_item_id",
                    "status": "planned"
                })
                print(f"   📋 计划修复需求 {req_data['req_id']}: 创建工作流项")

        # 修复测试用例文档
        test_cases_without_workflow = self.audit_results["details"]["missing_workflow_item_ids"]["test_cases_without_workflow"]
        for tc_data in test_cases_without_workflow:
            if not self.dry_run:
                try:
                    # 创建对应的工作流项
                    work_item = BusWorkItemDoc(
                        type_code="TEST_CASE",
                        title=f"[用例] {tc_data['title']}",
                        content=f"自动创建的测试用例工作流项 - {tc_data['case_id']}",
                        creator_id="system_repair",  # 使用系统标识
                        current_state="draft",  # 默认状态
                        current_owner_id=None
                    )

                    # 保存工作流项
                    await work_item.insert()

                    # 更新测试用例文档的 workflow_item_id
                    tc_doc = await TestCaseDoc.get(PydanticObjectId(tc_data["id"]))
                    if tc_doc:
                        tc_doc.workflow_item_id = str(work_item.id)
                        await tc_doc.save()

                    result["test_cases_repaired"] += 1
                    result["details"].append({
                        "type": "test_case",
                        "case_id": tc_data["case_id"],
                        "work_item_id": str(work_item.id),
                        "status": "success"
                    })

                    print(f"   ✅ 已为测试用例 {tc_data['case_id']} 创建工作流项 {str(work_item.id)}")

                except Exception as e:
                    result["details"].append({
                        "type": "test_case",
                        "case_id": tc_data["case_id"],
                        "status": "failed",
                        "error": str(e)
                    })
                    print(f"   ❌ 修复测试用例 {tc_data['case_id']} 失败: {e}")
            else:
                result["test_cases_repaired"] += 1
                result["details"].append({
                    "type": "test_case",
                    "case_id": tc_data["case_id"],
                    "action": "创建工作流项并更新 workflow_item_id",
                    "status": "planned"
                })
                print(f"   📋 计划修复测试用例 {tc_data['case_id']}: 创建工作流项")

        print(f"   总计: 需求 {result['requirements_repaired']} 个, 测试用例 {result['test_cases_repaired']} 个")
        return result

    async def repair_status_inconsistency(self) -> Dict[str, Any]:
        """修复状态不一致问题"""
        print("\n🔧 修复状态不一致问题...")

        result = {
            "description": "修复业务文档状态与工作流状态不一致的问题",
            "requirements_repaired": 0,
            "test_cases_repaired": 0,
            "details": []
        }

        # 修复需求状态不一致
        requirements_with_inconsistent_status = self.audit_results["details"]["status_inconsistency"]["requirements_with_inconsistent_status"]
        for req_inconsistency in requirements_with_inconsistent_status:
            if not self.dry_run:
                try:
                    # 同步需求状态到工作流状态
                    req_doc = await TestRequirementDoc.get(PydanticObjectId(req_inconsistency["requirement_id"]))
                    if req_doc:
                        req_doc.status = req_inconsistency["work_item_state"]
                        await req_doc.save()

                        result["requirements_repaired"] += 1
                        result["details"].append({
                            "type": "requirement",
                            "req_id": req_inconsistency["req_id"],
                            "old_status": req_inconsistency["requirement_status"],
                            "new_status": req_inconsistency["work_item_state"],
                            "status": "success"
                        })

                        print(f"   ✅ 同步需求 {req_inconsistency['req_id']} 状态: {req_inconsistency['requirement_status']} → {req_inconsistency['work_item_state']}")

                except Exception as e:
                    result["details"].append({
                        "type": "requirement",
                        "req_id": req_inconsistency["req_id"],
                        "status": "failed",
                        "error": str(e)
                    })
                    print(f"   ❌ 修复需求 {req_inconsistency['req_id']} 状态失败: {e}")
            else:
                result["requirements_repaired"] += 1
                result["details"].append({
                    "type": "requirement",
                    "req_id": req_inconsistency["req_id"],
                    "action": f"同步状态: {req_inconsistency['requirement_status']} → {req_inconsistency['work_item_state']}",
                    "status": "planned"
                })
                print(f"   📋 计划同步需求 {req_inconsistency['req_id']} 状态: {req_inconsistency['requirement_status']} → {req_inconsistency['work_item_state']}")

        # 修复测试用例状态不一致
        test_cases_with_inconsistent_status = self.audit_results["details"]["status_inconsistency"]["test_cases_with_inconsistent_status"]
        for tc_inconsistency in test_cases_with_inconsistent_status:
            if not self.dry_run:
                try:
                    # 同步测试用例状态到工作流状态
                    tc_doc = await TestCaseDoc.get(PydanticObjectId(tc_inconsistency["test_case_id"]))
                    if tc_doc:
                        tc_doc.status = tc_inconsistency["work_item_state"]
                        await tc_doc.save()

                        result["test_cases_repaired"] += 1
                        result["details"].append({
                            "type": "test_case",
                            "case_id": tc_inconsistency["case_id"],
                            "old_status": tc_inconsistency["test_case_status"],
                            "new_status": tc_inconsistency["work_item_state"],
                            "status": "success"
                        })

                        print(f"   ✅ 同步测试用例 {tc_inconsistency['case_id']} 状态: {tc_inconsistency['test_case_status']} → {tc_inconsistency['work_item_state']}")

                except Exception as e:
                    result["details"].append({
                        "type": "test_case",
                        "case_id": tc_inconsistency["case_id"],
                        "status": "failed",
                        "error": str(e)
                    })
                    print(f"   ❌ 修复测试用例 {tc_inconsistency['case_id']} 状态失败: {e}")
            else:
                result["test_cases_repaired"] += 1
                result["details"].append({
                    "type": "test_case",
                    "case_id": tc_inconsistency["case_id"],
                    "action": f"同步状态: {tc_inconsistency['test_case_status']} → {tc_inconsistency['work_item_state']}",
                    "status": "planned"
                })
                print(f"   📋 计划同步测试用例 {tc_inconsistency['case_id']} 状态: {tc_inconsistency['test_case_status']} → {tc_inconsistency['work_item_state']}")

        print(f"   总计: 需求 {result['requirements_repaired']} 个, 测试用例 {result['test_cases_repaired']} 个")
        return result

    async def repair_delete_inconsistency(self) -> Dict[str, Any]:
        """修复删除状态不一致问题"""
        print("\n🔧 修复删除状态不一致问题...")

        result = {
            "description": "修复删除状态不一致的问题",
            "business_docs_deleted": 0,
            "work_items_deleted": 0,
            "details": []
        }

        # 修复业务文档删除但工作流项活跃的问题
        business_deleted_workitem_active = self.audit_results["details"]["delete_inconsistency"]["business_deleted_workitem_active"]
        for inconsistency in business_deleted_workitem_active:
            if not self.dry_run:
                try:
                    # 删除对应的工作流项
                    work_item = await BusWorkItemDoc.get(PydanticObjectId(inconsistency["work_item_id"]))
                    if work_item:
                        work_item.is_deleted = True
                        await work_item.save()

                        result["work_items_deleted"] += 1
                        result["details"].append({
                            "type": "work_item",
                            "work_item_id": inconsistency["work_item_id"],
                            "business_doc_type": inconsistency["business_doc_type"],
                            "action": "删除工作流项以保持删除状态同步",
                            "status": "success"
                        })

                        print(f"   ✅ 删除工作流项 {inconsistency['work_item_id']} 以匹配业务文档删除状态")

                except Exception as e:
                    result["details"].append({
                        "type": "work_item",
                        "work_item_id": inconsistency["work_item_id"],
                        "status": "failed",
                        "error": str(e)
                    })
                    print(f"   ❌ 删除工作流项 {inconsistency['work_item_id']} 失败: {e}")
            else:
                result["work_items_deleted"] += 1
                result["details"].append({
                    "type": "work_item",
                    "work_item_id": inconsistency["work_item_id"],
                    "business_doc_type": inconsistency["business_doc_type"],
                    "action": "删除工作流项以保持删除状态同步",
                    "status": "planned"
                })
                print(f"   📋 计划删除工作流项 {inconsistency['work_item_id']}")

        # 修复工作流项删除但业务文档活跃的问题
        workitem_deleted_business_active = self.audit_results["details"]["delete_inconsistency"]["workitem_deleted_business_active"]
        for inconsistency in workitem_deleted_business_active:
            if not self.dry_run:
                try:
                    # 删除对应的业务文档
                    if inconsistency["business_doc_type"] == "requirement":
                        req_doc = await TestRequirementDoc.get(PydanticObjectId(inconsistency["business_doc_id"]))
                        if req_doc:
                            req_doc.is_deleted = True
                            await req_doc.save()

                            result["business_docs_deleted"] += 1
                            result["details"].append({
                                "type": "requirement",
                                "req_id": inconsistency["business_doc_identifier"],
                                "action": "删除需求以保持删除状态同步",
                                "status": "success"
                            })

                            print(f"   ✅ 删除需求 {inconsistency['business_doc_identifier']} 以匹配工作流项删除状态")

                    elif inconsistency["business_doc_type"] == "test_case":
                        tc_doc = await TestCaseDoc.get(PydanticObjectId(inconsistency["business_doc_id"]))
                        if tc_doc:
                            tc_doc.is_deleted = True
                            await tc_doc.save()

                            result["business_docs_deleted"] += 1
                            result["details"].append({
                                "type": "test_case",
                                "case_id": inconsistency["business_doc_identifier"],
                                "action": "删除测试用例以保持删除状态同步",
                                "status": "success"
                            })

                            print(f"   ✅ 删除测试用例 {inconsistency['business_doc_identifier']} 以匹配工作流项删除状态")

                except Exception as e:
                    result["details"].append({
                        "type": inconsistency["business_doc_type"],
                        "business_doc_id": inconsistency["business_doc_id"],
                        "status": "failed",
                        "error": str(e)
                    })
                    print(f"   ❌ 删除业务文档 {inconsistency['business_doc_identifier']} 失败: {e}")
            else:
                result["business_docs_deleted"] += 1
                result["details"].append({
                    "type": inconsistency["business_doc_type"],
                    "business_doc_id": inconsistency["business_doc_id"],
                    "action": "删除业务文档以保持删除状态同步",
                    "status": "planned"
                })
                print(f"   📋 计划删除{inconsistency['business_doc_type']} {inconsistency['business_doc_identifier']}")

        print(f"   总计: 删除工作流项 {result['work_items_deleted']} 个, 删除业务文档 {result['business_docs_deleted']} 个")
        return result

    async def repair_parent_child_inconsistency(self) -> Dict[str, Any]:
        """修复父子关系不一致问题"""
        print("\n🔧 修复父子关系不一致问题...")

        result = {
            "description": "修复父子关系不一致的问题",
            "parent_relations_repaired": 0,
            "details": []
        }

        inconsistent_parent_child_relations = self.audit_results["details"]["parent_child_inconsistency"]["inconsistent_parent_child_relations"]
        for inconsistency in inconsistent_parent_child_relations:
            if not self.dry_run:
                try:
                    # 修正父工作流项的 parent_item_id
                    tc_work_item = await BusWorkItemDoc.get(PydanticObjectId(inconsistency["test_case_work_item_id"]))
                    if tc_work_item and inconsistency["req_work_item_id"]:
                        tc_work_item.parent_item_id = PydanticObjectId(inconsistency["req_work_item_id"])
                        await tc_work_item.save()

                        result["parent_relations_repaired"] += 1
                        result["details"].append({
                            "type": "parent_child_relation",
                            "test_case_work_item_id": inconsistency["test_case_work_item_id"],
                            "old_parent_item_id": inconsistency["tc_parent_item_id"],
                            "new_parent_item_id": inconsistency["req_work_item_id"],
                            "referenced_req_id": inconsistency["referenced_req_id"],
                            "status": "success"
                        })

                        print(f"   ✅ 修正测试用例 {inconsistency['test_case_identifier']} 的父工作流项关系: {inconsistency['tc_parent_item_id']} → {inconsistency['req_work_item_id']}")

                except Exception as e:
                    result["details"].append({
                        "type": "parent_child_relation",
                        "test_case_work_item_id": inconsistency["test_case_work_item_id"],
                        "status": "failed",
                        "error": str(e)
                    })
                    print(f"   ❌ 修正测试用例 {inconsistency['test_case_identifier']} 父子关系失败: {e}")
            else:
                result["parent_relations_repaired"] += 1
                result["details"].append({
                    "type": "parent_child_relation",
                    "test_case_work_item_id": inconsistency["test_case_work_item_id"],
                    "action": f"修正父工作流项: {inconsistency['tc_parent_item_id']} → {inconsistency['req_work_item_id']}",
                    "referenced_req_id": inconsistency["referenced_req_id"],
                    "status": "planned"
                })
                print(f"   📋 计划修正测试用例 {inconsistency['test_case_identifier']} 父子关系: {inconsistency['tc_parent_item_id']} → {inconsistency['req_work_item_id']}")

        print(f"   总计: 修正父子关系 {result['parent_relations_repaired']} 个")
        return result

    async def run_repair_operations(self, operations: List[str]) -> Dict[str, Any]:
        """运行指定的修复操作"""
        print(f"🚀 开始执行修复操作: {', '.join(operations)}")

        try:
            await self.connect_to_mongodb()

            # 执行修复操作
            if "fix_missing_workflow" in operations:
                self.repair_results["details"]["missing_workflow_item_ids"] = await self.repair_missing_workflow_item_ids()

            if "fix_status" in operations:
                self.repair_results["details"]["status_inconsistency"] = await self.repair_status_inconsistency()

            if "fix_delete" in operations:
                self.repair_results["details"]["delete_inconsistency"] = await self.repair_delete_inconsistency()

            if "fix_parent_child" in operations:
                self.repair_results["details"]["parent_child_inconsistency"] = await self.repair_parent_child_inconsistency()

            # 生成总结
            self.repair_results["summary"] = {
                "missing_workflow_item_ids": self.repair_results["details"].get("missing_workflow_item_ids", {}).get("requirements_repaired", 0) + self.repair_results["details"].get("missing_workflow_item_ids", {}).get("test_cases_repaired", 0),
                "status_inconsistency": self.repair_results["details"].get("status_inconsistency", {}).get("requirements_repaired", 0) + self.repair_results["details"].get("status_inconsistency", {}).get("test_cases_repaired", 0),
                "delete_inconsistency": self.repair_results["details"].get("delete_inconsistency", {}).get("business_docs_deleted", 0) + self.repair_results["details"].get("delete_inconsistency", {}).get("work_items_deleted", 0),
                "parent_child_inconsistency": self.repair_results["details"].get("parent_child_inconsistency", {}).get("parent_relations_repaired", 0)
            }

            total_repaired = sum(self.repair_results["summary"].values())
            print(f"\n✅ 修复完成！总共修复 {total_repaired} 个问题")

        except Exception as e:
            print(f"❌ 修复失败: {e}")
            raise
        finally:
            await self.disconnect_from_mongodb()

        return self.repair_results

    def save_repair_report(self, output_file: Optional[str] = None):
        """保存修复报告"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mode = "dry_run" if self.dry_run else "actual"
            output_file = f"repair_workflow_consistency_{mode}_{timestamp}.json"

        output_path = Path(output_file)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.repair_results, f, indent=2, ensure_ascii=False)

        print(f"📄 修复报告已保存到: {output_path}")

        return str(output_path)


def load_audit_results(audit_file: str) -> Dict[str, Any]:
    """加载审计结果文件"""
    audit_path = Path(audit_file)
    if not audit_path.exists():
        raise FileNotFoundError(f"审计结果文件不存在: {audit_file}")

    with open(audit_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="工作流一致性修复工具")
    parser.add_argument("--audit-file", required=True, help="审计结果文件路径")
    parser.add_argument("--dry-run", action="store_true", help="仅显示计划操作，不实际执行")
    parser.add_argument("--fix-missing-workflow", action="store_true", help="修复缺失 workflow_item_id 的问题")
    parser.add_argument("--fix-status", action="store_true", help="修复状态不一致问题")
    parser.add_argument("--fix-delete", action="store_true", help="修复删除状态不一致问题")
    parser.add_argument("--fix-parent-child", action="store_true", help="修复父子关系不一致问题")
    parser.add_argument("--fix-all", action="store_true", help="执行所有修复操作")

    args = parser.parse_args()

    # 确定要执行的修复操作
    operations = []
    if args.fix_all:
        operations = ["fix_missing_workflow", "fix_status", "fix_delete", "fix_parent_child"]
    else:
        if args.fix_missing_workflow:
            operations.append("fix_missing_workflow")
        if args.fix_status:
            operations.append("fix_status")
        if args.fix_delete:
            operations.append("fix_delete")
        if args.fix_parent_child:
            operations.append("fix_parent_child")

    if not operations:
        print("❌ 请指定至少一个修复操作或使用 --fix-all")
        return

    # 加载审计结果
    try:
        audit_results = load_audit_results(args.audit_file)
        print(f"✅ 成功加载审计结果: {args.audit_file}")
    except Exception as e:
        print(f"❌ 加载审计结果失败: {e}")
        return

    # 创建修复器并执行修复
    repairer = WorkflowConsistencyRepairer(audit_results, args.dry_run)

    try:
        asyncio.run(repairer.run_repair_operations(operations))

        # 保存修复报告
        report_file = repairer.save_repair_report()

        # 输出摘要
        print("\n📊 修复摘要:")
        summary = repairer.repair_results["summary"]
        print(f"   缺失 workflow_item_id: {summary['missing_workflow_item_ids']} 个")
        print(f"   状态不一致: {summary['status_inconsistency']} 个")
        print(f"   删除状态不一致: {summary['delete_inconsistency']} 个")
        print(f"   父子关系不一致: {summary['parent_child_inconsistency']} 个")
        print(f"   总计修复: {sum(summary.values())} 个")

        return report_file

    except Exception as e:
        print(f"❌ 修复过程失败: {e}")
        return None


if __name__ == "__main__":
    main()