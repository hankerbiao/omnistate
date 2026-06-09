#!/usr/bin/env python3
"""
完整数据链造数脚本
===================

创建需求 -> 创建测试用例 -> 分配给不同角色 -> 流转 -> 创建执行计划 -> 分配执行任务

不同角色的用户在自己的"我的任务"页面能看到自己的待办事项。

使用方式:
    cd backend
    PYTHONPATH=. python scripts/seed_complete_flow.py
"""

import asyncio
import sys
from datetime import date, datetime, timezone
from typing import List, Optional
from bson import ObjectId

sys.path.insert(0, '.')

from pymongo import AsyncMongoClient
from app.shared.config.settings import get_settings
from app.shared.auth import create_access_token


# ═══════════════════════════════════════════════════════════════════════
# 测试数据配置
# ═══════════════════════════════════════════════════════════════════════

# 角色定义
ROLES = {
    "tpm": "TPM",           # 测试项目经理
    "dev": "MANUAL_DEV",    # 手动测试开发工程师
    "qa": "QA",             # 质量保证工程师
    "automation": "AUTO_DEV", # 自动化测试开发工程师
    "reviewer": "REVIEWER", # 评审者
}

# 测试场景：服务器厂商 BMC Web 管理界面功能验证
SCENARIO = {
    "name": "BMC Web UI 功能验证项目",
    "description": "验证服务器 BMC Web 管理界面的核心功能，包括用户管理、网络配置、告警管理、日志查看等",
    "requirements": [
        {
            "req_id": "TR-2026-00201",
            "title": "BMC Web UI 用户管理功能验证",
            "description": "验证 BMC Web 管理界面中的用户管理功能，包括用户创建、编辑、删除、密码策略和权限分配",
            "priority": "P0",
            "category": "FUNCTIONAL",
            "tags": ["BMC", "Web UI", "用户管理"],
            "test_cases": [
                {
                    "case_id": "TC-BMC-UI-001",
                    "title": "Web UI 用户创建功能验证",
                    "priority": "P0",
                    "pre_condition": "BMC Web 管理界面正常访问，具有管理员权限",
                    "post_condition": "新用户成功创建，可使用该用户登录",
                    "estimated_duration_sec": 300,
                    "assignee": "dev",
                    "type": "manual",
                },
                {
                    "case_id": "TC-BMC-UI-002",
                    "title": "Web UI 用户权限分配验证",
                    "priority": "P0",
                    "pre_condition": "已创建测试用户和角色",
                    "post_condition": "权限分配生效，用户只能访问授权资源",
                    "estimated_duration_sec": 300,
                    "assignee": "dev",
                    "type": "manual",
                },
                {
                    "case_id": "TC-BMC-UI-003",
                    "title": "Web UI 密码策略配置验证",
                    "priority": "P1",
                    "pre_condition": "BMC 具有密码策略配置权限",
                    "post_condition": "密码策略生效，不符合策略的密码被拒绝",
                    "estimated_duration_sec": 180,
                    "assignee": "qa",
                    "type": "manual",
                },
            ],
        },
        {
            "req_id": "TR-2026-00202",
            "title": "BMC Web UI 网络配置功能验证",
            "description": "验证 BMC Web 管理界面中的网络配置功能，包括 IP 设置、DNS 配置、网络接口管理等",
            "priority": "P1",
            "category": "FUNCTIONAL",
            "tags": ["BMC", "Web UI", "网络配置"],
            "test_cases": [
                {
                    "case_id": "TC-BMC-UI-004",
                    "title": "Web UI 静态 IP 配置验证",
                    "priority": "P0",
                    "pre_condition": "BMC 网络接口可用",
                    "post_condition": "静态 IP 配置成功，新 IP 可访问",
                    "estimated_duration_sec": 600,
                    "assignee": "qa",
                    "type": "manual",
                },
                {
                    "case_id": "TC-BMC-UI-005",
                    "title": "Web UI DNS 服务器配置验证",
                    "priority": "P1",
                    "pre_condition": "BMC 网络配置页面可访问",
                    "post_condition": "DNS 配置成功，主机名解析正常",
                    "estimated_duration_sec": 300,
                    "assignee": "qa",
                    "type": "manual",
                },
            ],
        },
        {
            "req_id": "TR-2026-00203",
            "title": "BMC Web UI 告警与日志功能验证",
            "description": "验证 BMC Web 管理界面中的告警管理和日志查看功能",
            "priority": "P1",
            "category": "FUNCTIONAL",
            "tags": ["BMC", "Web UI", "告警", "日志"],
            "test_cases": [
                {
                    "case_id": "TC-BMC-UI-006",
                    "title": "Web UI 实时告警监控验证",
                    "priority": "P0",
                    "pre_condition": "BMC 告警监控页面可用",
                    "post_condition": "告警实时推送，正常显示",
                    "estimated_duration_sec": 300,
                    "assignee": "qa",
                    "type": "manual",
                },
                {
                    "case_id": "TC-BMC-UI-007",
                    "title": "Web UI 系统日志导出验证",
                    "priority": "P2",
                    "pre_condition": "存在系统日志数据",
                    "post_condition": "日志成功导出，格式正确",
                    "estimated_duration_sec": 180,
                    "assignee": "dev",
                    "type": "manual",
                },
            ],
        },
        {
            "req_id": "TR-2026-00204",
            "title": "BMC Web UI 自动化测试脚本开发",
            "description": "开发 BMC Web UI 功能自动化测试脚本，使用 Selenium + Python",
            "priority": "P1",
            "category": "AUTOMATION",
            "tags": ["BMC", "自动化", "Selenium"],
            "test_cases": [
                {
                    "case_id": "TC-BMC-AUTO-001",
                    "title": "用户管理自动化测试脚本",
                    "priority": "P1",
                    "pre_condition": "Selenium 环境已配置",
                    "post_condition": "自动化脚本可重复执行，覆盖用户管理关键路径",
                    "estimated_duration_sec": 1800,
                    "assignee": "automation",
                    "type": "auto",
                },
                {
                    "case_id": "TC-BMC-AUTO-002",
                    "title": "网络配置自动化测试脚本",
                    "priority": "P1",
                    "pre_condition": "Selenium 环境已配置，测试机可访问 BMC",
                    "post_condition": "网络配置自动化脚本稳定运行",
                    "estimated_duration_sec": 1800,
                    "assignee": "automation",
                    "type": "auto",
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════

def now_utc():
    return datetime.now(timezone.utc)


async def upsert_workflow_item(
    db,
    item_id: str,
    type_code: str,
    title: str,
    content: str,
    creator_id: str,
    owner_id: str,
    current_state: str = "DRAFT",
) -> dict:
    """创建或更新工作流事项 (BusWorkItemDoc)"""
    doc = {
        "item_id": item_id,
        "type_code": type_code,
        "title": title,
        "content": content,
        "parent_item_id": None,
        "current_state": current_state,
        "current_owner_id": owner_id,
        "creator_id": creator_id,
        "is_deleted": False,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    await db.bus_work_items.update_one(
        {"item_id": item_id},
        {"$setOnInsert": doc},
        upsert=True,
    )
    return doc


async def upsert_test_case(
    db,
    case_id: str,
    lab_id: str,
    title: str,
    pre_condition: str,
    post_condition: str,
    priority: str,
    estimated_duration_sec: int,
    ref_req_id: str,
    catalog_path: List[str],
    owner_id: str,
) -> dict:
    """创建或更新测试用例"""
    path_norm = [p.lower() for p in catalog_path]
    doc = {
        "case_id": case_id,
        "lab_id": lab_id,
        "title": title,
        "version": 1,
        "is_active": True,
        "owner_id": owner_id,
        "priority": priority,
        "estimated_duration_sec": estimated_duration_sec,
        "ref_req_id": ref_req_id,
        "catalog_path": path_norm,
        "catalog_path_key": "/".join(path_norm),
        "required_env": {
            "server_type": "2U Rack Server",
            "platform": "x86_64",
            "vendor_domain": "server",
            "test_type": "BMC Web UI",
        },
        "tags": ["BMC", "Web UI"],
        "test_category": "功能测试",
        "is_destructive": False,
        "pre_condition": pre_condition,
        "post_condition": post_condition,
        "risk_level": "高" if priority in ("P0", "P1") else "中",
        "failure_analysis": "检查 BMC 服务状态、网络连接、浏览器兼容性。",
        "confidentiality": "internal",
        "visibility_scope": "team",
        "steps": [
            {
                "step_id": "S1",
                "name": "准备测试环境",
                "action": pre_condition,
                "expected": "测试环境就绪",
            },
            {
                "step_id": "S2",
                "name": "执行测试步骤",
                "action": f"在 BMC Web UI 中执行 {title} 相关操作",
                "expected": post_condition,
            },
            {
                "step_id": "S3",
                "name": "记录测试结果",
                "action": "记录测试通过/失败，必要时截图",
                "expected": "测试结果文档完整",
            },
        ],
        "cleanup_steps": [
            {"step_id": "C1", "name": "恢复配置", "action": "恢复测试环境配置", "expected": "配置已恢复"},
            {"step_id": "C2", "name": "清理数据", "action": "清理测试数据", "expected": "数据已清理"},
        ],
        "approval_history": [],
        "custom_fields": {},
        "attachments": [],
        "is_deleted": False,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    await db.test_cases.update_one(
        {"case_id": case_id},
        {"$setOnInsert": doc},
        upsert=True,
    )
    return doc


async def create_execution_plan(
    db,
    plan_id: str,
    title: str,
    description: str,
    creator_id: str,
) -> dict:
    """创建执行计划"""
    doc = {
        "plan_id": plan_id,
        "title": title,
        "description": description,
        "creator_id": creator_id,
        "status": "draft",
        "planned_start_date": date.today().isoformat(),
        "planned_end_date": date.today().isoformat(),
        "is_deleted": False,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    await db.execution_plans.update_one(
        {"plan_id": plan_id},
        {"$setOnInsert": doc},
        upsert=True,
    )
    return doc


async def create_execution_plan_item(
    db,
    item_id: str,
    plan_id: str,
    case_id: str,
    case_title: str,
    priority: str,
    component: str,
    assignee_id: str,
    ref_type: str,
    order_no: int,
) -> dict:
    """创建执行计划条目"""
    doc = {
        "item_id": item_id,
        "plan_id": plan_id,
        "ref_type": ref_type,
        "case_id": case_id,
        "case_title": case_title,
        "priority": priority,
        "component": component,
        "assignee_id": assignee_id,
        "status": "pending",  # pending -> running -> done
        "order_no": order_no,
        "is_deleted": False,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    await db.execution_plan_items.update_one(
        {"item_id": item_id},
        {"$setOnInsert": doc},
        upsert=True,
    )
    return doc


# ═══════════════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════════════

async def main():
    settings = get_settings()
    client = AsyncMongoClient(settings.mongodb.uri)
    db = client[settings.mongodb.db_name]

    print("=" * 70)
    print("🚀 完整数据链造数脚本 - BMC Web UI 功能验证项目")
    print("=" * 70)

    # ── Step 1: 创建需求工作流事项 ──────────────────────────────────────
    print("\n📋 Step 1: 创建需求工作流事项")

    all_work_items = []  # 收集所有工作流事项
    all_test_cases = []  # 收集所有测试用例

    req_workflow_map = {}  # req_id -> work_item_id

    for req in SCENARIO["requirements"]:
        req_id = req["req_id"]
        # 创建需求的 BusWorkItemDoc
        req_workflow_id = f"WI-REQ-{req_id}"
        await upsert_workflow_item(
            db,
            item_id=req_workflow_id,
            type_code="REQUIREMENT",
            title=req["title"],
            content=req["description"],
            creator_id="tpm",
            owner_id="tpm",
            current_state="ASSIGNED",  # 分配给 TPM 处理
        )
        req_workflow_map[req_id] = req_workflow_id
        all_work_items.append({
            "item_id": req_workflow_id,
            "type": "REQUIREMENT",
            "assignee": "tpm",
            "title": req["title"],
        })
        print(f"  ✅ 创建需求工作流: {req_workflow_id} -> {req_id}")

        # 流转需求到开发阶段
        await db.bus_flow_logs.insert_one({
            "work_id": req_workflow_id,
            "action": "ASSIGN",
            "from_state": "DRAFT",
            "to_state": "ASSIGNED",
            "operator_id": "tpm",
            "is_deleted": False,
            "created_at": now_utc(),
        })

    # ── Step 2: 创建测试用例工作流事项 ─────────────────────────────────
    print("\n📝 Step 2: 创建测试用例工作流事项")

    tc_workflow_map = {}  # case_id -> work_item_id

    for req in SCENARIO["requirements"]:
        req_id = req["req_id"]
        for tc in req["test_cases"]:
            case_id = tc["case_id"]
            assignee = tc["assignee"]

            # 创建测试用例的 BusWorkItemDoc
            tc_workflow_id = f"WI-TC-{case_id}"
            await upsert_workflow_item(
                db,
                item_id=tc_workflow_id,
                type_code="TEST_CASE",
                title=tc["title"],
                content=f"参考需求: {req_id}\n前置条件: {tc['pre_condition']}",
                creator_id="tpm",
                owner_id=assignee,  # 分配给对应的角色
                current_state="ASSIGNED",
            )
            tc_workflow_map[case_id] = tc_workflow_id
            all_work_items.append({
                "item_id": tc_workflow_id,
                "type": "TEST_CASE",
                "assignee": assignee,
                "title": tc["title"],
            })

            # 创建测试用例文档
            await upsert_test_case(
                db,
                case_id=case_id,
                lab_id="LAB-BMC",
                title=tc["title"],
                pre_condition=tc["pre_condition"],
                post_condition=tc["post_condition"],
                priority=tc["priority"],
                estimated_duration_sec=tc["estimated_duration_sec"],
                ref_req_id=req_id,
                catalog_path=["BMC Web UI", req["tags"][1] if len(req["tags"]) > 1 else req["tags"][0]],
                owner_id=assignee,
            )
            all_test_cases.append({
                "case_id": case_id,
                "assignee": assignee,
                "title": tc["title"],
                "type": tc["type"],
            })

            print(f"  ✅ 创建测试用例: {tc_workflow_id} -> {case_id} (分配给: {assignee})")

            # 记录流转
            await db.bus_flow_logs.insert_one({
                "work_id": tc_workflow_id,
                "action": "ASSIGN",
                "from_state": "DRAFT",
                "to_state": "ASSIGNED",
                "operator_id": "tpm",
                "is_deleted": False,
                "created_at": now_utc(),
            })

    # ── Step 3: 创建执行计划 ────────────────────────────────────────────
    print("\n📊 Step 3: 创建执行计划")

    plan_id = "EP-2026-000005"
    await create_execution_plan(
        db,
        plan_id=plan_id,
        title=SCENARIO["name"],
        description=SCENARIO["description"],
        creator_id="tpm",
    )
    print(f"  ✅ 创建执行计划: {plan_id}")

    # ── Step 4: 创建执行计划条目 ────────────────────────────────────────
    print("\n📋 Step 4: 创建执行计划条目")

    item_counter = 1
    plan_items_by_assignee = {}  # 用于统计每个用户的任务数

    for req in SCENARIO["requirements"]:
        for tc in req["test_cases"]:
            case_id = tc["case_id"]
            assignee = tc["assignee"]

            item_id = f"EPI-2026-{str(500 + item_counter).zfill(6)}"
            await create_execution_plan_item(
                db,
                item_id=item_id,
                plan_id=plan_id,
                case_id=case_id,
                case_title=tc["title"],
                priority=tc["priority"],
                component="bmc",
                assignee_id=assignee,
                ref_type=tc["type"],
                order_no=item_counter - 1,
            )

            if assignee not in plan_items_by_assignee:
                plan_items_by_assignee[assignee] = []
            plan_items_by_assignee[assignee].append(case_id)

            print(f"  ✅ 创建执行计划条目: {item_id} -> {case_id} (分配给: {assignee})")
            item_counter += 1

    # ── Step 5: 统计结果 ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("📈 数据链创建完成 - 统计汇总")
    print("=" * 70)

    # 按角色统计工作流事项
    print("\n🔹 工作流事项按角色分布:")
    from collections import Counter
    workflow_by_role = Counter(item["assignee"] for item in all_work_items)
    for role, count in workflow_by_role.items():
        print(f"   {role}: {count} 项")

    # 按角色统计执行计划条目
    print("\n🔹 执行计划条目按角色分布:")
    for role, case_ids in plan_items_by_assignee.items():
        print(f"   {role}: {len(case_ids)} 项")

    # ── Step 6: 验证每个角色的"我的任务"视图 ───────────────────────────
    print("\n" + "=" * 70)
    print("🔍 验证「我的任务」数据 - 按用户查询")
    print("=" * 70)

    for user_id in ["dev", "qa", "automation", "tpm", "reviewer"]:
        # 查询该用户的工作流事项
        workflow_items = await db.bus_work_items.find({
            "current_owner_id": user_id,
            "is_deleted": False,
        }).to_list(100)

        # 查询该用户的执行计划条目
        plan_items = await db.execution_plan_items.find({
            "assignee_id": user_id,
            "is_deleted": False,
            "archived_at": None,
        }).to_list(100)

        total_tasks = len(workflow_items) + len(plan_items)
        if total_tasks > 0:
            print(f"\n👤 用户 '{user_id}' 的任务 ({total_tasks} 项):")
            for wi in workflow_items[:3]:
                print(f"   📋 工作流: {wi['type_code']} - {wi['title'][:30]}...")
            for pi in plan_items[:3]:
                print(f"   📝 执行任务: {pi['case_id']} - {pi['case_title'][:25]}...")
            if len(workflow_items) > 3 or len(plan_items) > 3:
                remaining = total_tasks - 6
                if remaining > 0:
                    print(f"   ... 还有 {remaining} 项")

    # 最终确认
    total_workflow = await db.bus_work_items.count_documents({"is_deleted": False})
    total_plan_items = await db.execution_plan_items.count_documents({"is_deleted": False, "archived_at": None})
    total_results = await db.execution_plan_results.count_documents({})
    total_cases = await db.test_cases.count_documents({})

    print("\n" + "=" * 70)
    print("✅ 数据库状态确认")
    print("=" * 70)
    print(f"   Bus Work Items (工作流事项): {total_workflow}")
    print(f"   Execution Plan Items (执行任务): {total_plan_items}")
    print(f"   Execution Plan Results (结果): {total_results}")
    print(f"   Test Cases (测试用例): {total_cases}")

    print("\n" + "=" * 70)
    print("🎉 完整数据链创建成功!")
    print("=" * 70)
    print("""
数据链路:
  需求 (TPM 创建)
    → 测试用例 (分配给 dev/qa/automation)
    → 执行计划 (TPM 创建)
    → 执行计划条目 (分配给对应角色)

不同角色的"我的任务"视图:
  - dev (测试开发工程师): 查看自己被分配的测试用例开发任务
  - qa (质量保证工程师): 查看测试执行任务
  - automation (自动化工程师): 查看自动化脚本开发任务
  - tpm (项目经理): 查看需求管理和项目协调任务
    """)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())