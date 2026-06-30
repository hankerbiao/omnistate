#!/usr/bin/env python3
"""
模拟数据生成脚本 — 批量创建项目、需求、用例等关联数据。

直接使用 Beanie ODM 写入 MongoDB，不依赖后端 API 运行。
前提：必须先执行 scripts/init/init_rbac.py 和 scripts/init/seed_test_users.py。

用法:
  python scripts/mock/seed_mock_data.py                          # 创建全部模拟数据
  python scripts/mock/seed_mock_data.py --reset                  # 覆盖已存在数据
  python scripts/mock/seed_mock_data.py --project-only           # 只创建项目
  python scripts/mock/seed_mock_data.py --no-cases               # 不创建测试用例
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.shared.config import get_settings
from app.modules.auth.repository.models import UserDoc
from app.modules.project.repository.models.project import ProjectDoc
from app.modules.test_specs.repository.models.requirement import TestRequirementDoc
from app.modules.test_specs.repository.models.test_case import TestCaseDoc, TestCaseStepEmbedded
from app.modules.execution_plan.repository.models.execution_plan import (
    ExecutionPlanDoc,
    ExecutionPlanItemDoc,
)


# ──────────────────────────────────────────────
#  数据定义
# ──────────────────────────────────────────────

PROJECTS = [
    {
        "project_id": "PRJ-2026-00001",
        "key": "REDFISH-V3",
        "name": "Redfish 协议 V3 认证",
        "description": "Redfish 可管理性规范 V3 版本的功能验证与合规性测试",
        "status": "active",
        "priority": "P0",
        "target_version": "V3.0",
        "tags": ["Redfish", "可管理性", "协议认证"],
    },
    {
        "project_id": "PRJ-2026-00002",
        "key": "DDR5-VAL",
        "name": "DDR5 内存子系统验证",
        "description": "DDR5 内存控制器及 PHY 层功能验证，覆盖 4800/5600 MT/s 两档速率",
        "status": "active",
        "priority": "P1",
        "target_version": "V1.0",
        "tags": ["DDR5", "内存", "PHY"],
    },
    {
        "project_id": "PRJ-2026-00003",
        "key": "SEC-BOOT",
        "name": "安全启动链验证",
        "description": "固件安全启动流程验证，包含签名验证、测量启动、回滚保护",
        "status": "active",
        "priority": "P1",
        "target_version": "V2.1",
        "tags": ["安全", "启动", "固件"],
    },
]

REQUIREMENTS_DATA = [
    # Redfish 项目需求
    {
        "req_id": "TR-2026-00001",
        "title": "Redfish 基本资源模型查询",
        "description": "验证 Redfish 标准资源模型的 GET 操作，包括 /redfish/v1/, /Systems/, /Chassis/, /Managers/ 等入口点",
        "category": "FUNCTIONAL",
        "priority": "P0",
        "source": "SPEC",
        "tags": ["Redfish", "资源模型"],
        "target_components": ["BMC", "Redfish Service"],
        "acceptance_criteria": "所有标准资源路径返回 200，JSON Schema 符合 Redfish 规范",
        "project_id": "PRJ-2026-00001",
    },
    {
        "req_id": "TR-2026-00002",
        "title": "Redfish 事件订阅与推送",
        "description": "验证 EventService 的事件订阅、推送和重试机制",
        "category": "FUNCTIONAL",
        "priority": "P1",
        "source": "SPEC",
        "tags": ["Redfish", "事件"],
        "target_components": ["BMC", "EventService"],
        "acceptance_criteria": "支持 SSE 和 SNMP 两种推送方式，断连后自动重试 3 次",
        "project_id": "PRJ-2026-00001",
    },
    # DDR5 项目需求
    {
        "req_id": "TR-2026-00003",
        "title": "DDR5 基础功能读写验证",
        "description": "验证 DDR5 内存的基础读写功能，覆盖单通道和双通道模式",
        "category": "FUNCTIONAL",
        "priority": "P1",
        "source": "INTERNAL",
        "tags": ["DDR5", "功能"],
        "target_components": ["Memory Controller", "DIMM"],
        "acceptance_criteria": "读写带宽不低于 4800 MT/s，数据一致性 100%",
        "project_id": "PRJ-2026-00002",
    },
    {
        "req_id": "TR-2026-00004",
        "title": "DDR5 压力与稳定性测试",
        "description": "长时间压力负载下 DDR5 子系统的稳定性验证",
        "category": "STABILITY",
        "priority": "P1",
        "source": "INTERNAL",
        "tags": ["DDR5", "稳定性"],
        "target_components": ["Memory Controller", "DIMM"],
        "acceptance_criteria": "72 小时压力测试无 ECC 错误，温度在规格范围内",
        "project_id": "PRJ-2026-00002",
    },
    # 安全启动项目需求
    {
        "req_id": "TR-2026-00005",
        "title": "安全启动签名验证流程",
        "description": "验证固件启动过程中的数字签名验证机制",
        "category": "SECURITY",
        "priority": "P0",
        "source": "REGULATION",
        "tags": ["安全", "启动"],
        "target_components": ["BootROM", "Flash"],
        "acceptance_criteria": "篡改固件签名后启动被阻止，正确签名正常启动",
        "project_id": "PRJ-2026-00003",
    },
]

# 测试用例模板: (title_suffix, priority, test_category, risk_level, pre_cond, post_cond, tags, destructive, duration_sec, env)
CASE_TEMPLATES: list[tuple[str, ...]] = [
    ("正向流程 - 资源查询",
     "P0", "功能测试", "低",
     "BMC 正常运行，Redfish 服务已启动",
     "所有标准资源路径返回 200，JSON 结构正确",
     ["冒烟测试", "Redfish"], False, 180, {}),
    ("异常流程 - 无效资源路径",
     "P1", "功能测试", "中",
     "BMC 正常运行",
     "无效路径返回 404，错误信息符合 Redfish 规范",
     ["异常测试", "Redfish"], False, 120, {}),
    ("并发查询 - 多客户端同时访问",
     "P1", "性能测试", "高",
     "准备并发测试工具，BMC 正常运行",
     "并发下响应时间不超过 2s，无连接中断",
     ["性能测试", "并发"], False, 600, {"并发数": 50}),
    ("事件订阅 - SSE 推送验证",
     "P1", "功能测试", "中",
     "已创建事件订阅，SSE 客户端已连接",
     "资源变更后 SSE 客户端收到事件通知",
     ["Redfish", "事件"], False, 300, {}),
    ("事件推送 - 断连重试",
     "P2", "功能测试", "中",
     "已创建事件订阅，模拟网络断开",
     "网络恢复后自动重新建立推送连接",
     ["可靠性", "事件"], False, 600, {"重试次数": 3}),
    ("内存读写 - 单通道模式",
     "P0", "功能测试", "低",
     "DDR5 内存已安装，系统正常运行",
     "读写数据一致，带宽达到 4800 MT/s",
     ["DDR5", "冒烟测试"], False, 300, {"通道": "单通道"}),
    ("内存读写 - 双通道模式",
     "P0", "功能测试", "低",
     "双通道 DDR5 内存已安装",
     "读写数据一致，带宽达到 5600 MT/s",
     ["DDR5", "冒烟测试"], False, 300, {"通道": "双通道"}),
    ("内存压力 - 72 小时稳定性",
     "P1", "稳定性测试", "高",
     "DDR5 已安装，监控工具就绪",
     "72 小时内无 ECC 错误，温度不超过 85°C",
     ["DDR5", "稳定性"], False, 3600, {"时长_hours": 72}),
    ("内存压力 - 温度边界测试",
     "P2", "稳定性测试", "高",
     "DDR5 已安装，温箱就绪",
     "在 0°C~85°C 范围内功能正常",
     ["DDR5", "温度"], False, 1800, {"温度范围": "0~85°C"}),
    ("安全启动 - 正常签名验证",
     "P0", "安全测试", "低",
     "固件包含正确数字签名",
     "启动成功，日志记录签名验证通过",
     ["安全", "启动"], False, 120, {}),
    ("安全启动 - 篡改签名拒绝",
     "P0", "安全测试", "高",
     "固件签名已被篡改",
     "启动被阻止，返回安全错误码",
     ["安全", "启动"], False, 120, {}),
    ("安全启动 - 回滚保护验证",
     "P1", "安全测试", "中",
     "固件版本低于当前版本",
     "回滚被阻止，日志记录版本号",
     ["安全", "回滚"], False, 180, {}),
]

LAB_NAMES = ["SH", "SZ", "BJ"]
CATALOG_PATHS = [
    ["功能测试", "正向流程"],
    ["功能测试", "异常流程"],
    ["性能测试", "并发"],
    ["稳定性测试", "压力"],
    ["安全测试", "签名验证"],
]

STEP_TEMPLATES = [
    TestCaseStepEmbedded(step_id="step-1", name="环境准备", action="确认被测系统处于就绪状态，记录初始状态信息", expected="系统状态正常，日志无异常"),
    TestCaseStepEmbedded(step_id="step-2", name="执行测试", action="按测试方案执行具体操作步骤", expected="操作执行成功，返回预期结果"),
    TestCaseStepEmbedded(step_id="step-3", name="结果检查", action="检查输出结果是否符合预期，记录实际结果", expected="实际结果与预期一致"),
    TestCaseStepEmbedded(step_id="step-4", name="环境恢复", action="恢复测试环境到初始状态", expected="环境恢复完成，不影响后续测试"),
]


# ──────────────────────────────────────────────
#  辅助函数
# ──────────────────────────────────────────────

def _make_dates(days_ago_start: int, days_range: int) -> tuple[datetime, datetime]:
    """生成计划时间范围。"""
    start = datetime.now().astimezone() - timedelta(days=days_ago_start)
    end = start + timedelta(days=days_range)
    return start, end


# ──────────────────────────────────────────────
#  数据创建函数
# ──────────────────────────────────────────────

async def create_projects(owner_id: str, reset: bool) -> dict[str, str]:
    """创建项目，返回 {project_key: project_id} 映射。"""
    print("\n  [项目]")
    result = {}
    for pdata in PROJECTS:
        pid = pdata["project_id"]
        existing = await ProjectDoc.find_one(ProjectDoc.project_id == pid)
        if existing and not reset:
            print(f"    ✓ {pid} ({pdata['key']}) 已存在，跳过")
            result[pdata["key"]] = pid
            continue

        start, end = _make_dates(30, 90)
        doc = ProjectDoc(
            project_id=pid,
            key=pdata["key"],
            name=pdata["name"],
            description=pdata.get("description", ""),
            status=pdata["status"],
            priority=pdata["priority"],
            owner_id=owner_id,
            start_date=start,
            end_date=end,
            target_version=pdata.get("target_version", ""),
            tags=pdata.get("tags", []),
            created_by=owner_id,
        )
        if existing and reset:
            doc.id = existing.id
            await doc.replace()
            print(f"    ~ {pid} ({pdata['key']}) 已覆盖")
        else:
            await doc.insert()
            print(f"    + {pid} ({pdata['key']})")
        result[pdata["key"]] = pid
    return result


async def create_requirements(owner_id: str, project_map: dict[str, str], reset: bool):
    """创建需求并关联到项目。"""
    print("\n  [需求]")
    for rdata in REQUIREMENTS_DATA:
        rid = rdata["req_id"]
        existing = await TestRequirementDoc.find_one(TestRequirementDoc.req_id == rid)
        if existing and not reset:
            print(f"    ✓ {rid} 已存在，跳过")
            continue

        pid = project_map.get(rdata["project_id"])
        start, end = _make_dates(20, 60)
        doc = TestRequirementDoc(
            req_id=rid,
            title=rdata["title"],
            description=rdata.get("description", ""),
            category=rdata.get("category", ""),
            priority=rdata.get("priority", "P1"),
            source=rdata.get("source", ""),
            tags=rdata.get("tags", []),
            target_components=rdata.get("target_components", []),
            acceptance_criteria=rdata.get("acceptance_criteria", ""),
            tpm_owner_id=owner_id,
            planned_start_date=start.date() if start else None,
            planned_end_date=end.date() if end else None,
            project_ids=[pid] if pid else [],
        )
        if existing and reset:
            doc.id = existing.id
            await doc.replace()
            print(f"    ~ {rid} ({rdata['title'][:30]}...) 已覆盖")
        else:
            await doc.insert()
            print(f"    + {rid} ({rdata['title'][:30]}...)")
        # 更新需求到项目映射
        rdata["_id"] = rid


async def create_test_cases(owner_id: str, reviewer_id: str, project_map: dict[str, str], reset: bool):
    """创建测试用例并关联到需求和项目。"""
    # 加载已创建的需求
    requirements = await TestRequirementDoc.find(
        TestRequirementDoc.is_deleted == False  # noqa: E712
    ).to_list()

    if not requirements:
        print("\n  [测试用例]  ⚠ 没有找到需求，跳过")
        return

    print("\n  [测试用例]")
    count = 0
    for req in requirements:
        # 确定这个需求的项目 ID
        req_project_ids = req.project_ids or []
        # 找到该需求对应的模板子集
        req_index = next(
            (i for i, r in enumerate(REQUIREMENTS_DATA) if r["req_id"] == req.req_id),
            -1,
        )
        if req_index < 0:
            continue

        # 每个需求分配若干用例模板
        templates_for_req = CASE_TEMPLATES[req_index * 3:(req_index + 1) * 3]
        if not templates_for_req:
            templates_for_req = CASE_TEMPLATES[:3]

        for i, tmpl in enumerate(templates_for_req):
            suffix, priority, category, risk, pre_cond, post_cond, tags, destructive, duration, env = tmpl
            case_id = f"TC-{req.req_id.split('-')[-1]}-{i + 1:02d}"
            title = f"{req.title} - {suffix}"

            existing = await TestCaseDoc.find_one(TestCaseDoc.case_id == case_id)
            if existing and not reset:
                print(f"    ✓ {case_id} 已存在，跳过")
                count += 1
                continue

            lab = LAB_NAMES[count % len(LAB_NAMES)]
            catalog = CATALOG_PATHS[count % len(CATALOG_PATHS)]

            doc = TestCaseDoc(
                case_id=case_id,
                lab_id=lab,
                catalog_path=catalog,
                catalog_path_key="/".join(catalog).lower(),
                ref_req_id=req.req_id,
                title=title,
                version=1,
                is_active=True,
                owner_id=owner_id,
                reviewer_id=reviewer_id,
                priority=priority,
                test_category=category,
                risk_level=risk,
                pre_condition=pre_cond,
                post_condition=post_cond,
                tags=tags,
                is_destructive=destructive,
                estimated_duration_sec=duration,
                required_env=env,
                steps=STEP_TEMPLATES,
                project_ids=req_project_ids,
            )
            if existing and reset:
                doc.id = existing.id
                await doc.replace()
                print(f"    ~ {case_id} ({title[:40]}...) 已覆盖")
            else:
                await doc.insert()
                print(f"    + {case_id} ({title[:40]}...)")
            count += 1
    print(f"    共 {count} 个用例")


async def create_execution_plans(owner_id: str, reset: bool):
    """创建执行计划并关联用例。"""
    cases = await TestCaseDoc.find(
        TestCaseDoc.is_deleted == False  # noqa: E712
    ).to_list()
    if not cases:
        print("\n  [执行计划]  ⚠ 没有找到测试用例，跳过")
        return

    print("\n  [执行计划]")
    # 按 Lab 分组创建计划
    from collections import defaultdict
    by_lab: dict[str, list[TestCaseDoc]] = defaultdict(list)
    for c in cases:
        by_lab[c.lab_id].append(c)

    for lab, lab_cases in by_lab.items():
        plan_id = f"PLAN-{lab}-{datetime.now().strftime('%Y%m')}"
        existing = await ExecutionPlanDoc.find_one(ExecutionPlanDoc.plan_id == plan_id)
        if existing and not reset:
            print(f"    ✓ {plan_id} 已存在，跳过")
            continue

        start, end = _make_dates(7, 14)
        plan = ExecutionPlanDoc(
            plan_id=plan_id,
            title=f"{lab} Lab 月度执行计划 ({datetime.now().strftime('%Y-%m')})",
            description=f"{lab} 实验室本月自动化执行计划，涵盖 {len(lab_cases)} 个用例",
            status="active",
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            created_by=owner_id,
            item_count=len(lab_cases),
        )
        if existing and reset:
            plan.id = existing.id
            await plan.replace()
            print(f"    ~ {plan_id} ({plan.title}) 已覆盖")
        else:
            await plan.insert()
            print(f"    + {plan_id} ({plan.title})")

        # 创建计划条目
        for idx, c in enumerate(lab_cases):
            item_id = f"{plan_id}-ITEM-{idx + 1:03d}"
            existing_item = await ExecutionPlanItemDoc.find_one(
                ExecutionPlanItemDoc.item_id == item_id
            )
            if existing_item and not reset:
                continue

            item = ExecutionPlanItemDoc(
                item_id=item_id,
                plan_id=plan_id,
                ref_type="manual",
                case_id=c.case_id,
                case_title=c.title,
                priority=c.priority or "",
                assignee_id=owner_id,
                status="pending",
                order_no=idx + 1,
            )
            await item.insert()
        print(f"      ↳ {len(lab_cases)} 个计划条目")


# ──────────────────────────────────────────────
#  主流程
# ──────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description="模拟数据生成器 — 批量创建项目、需求、用例、执行计划",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--reset", action="store_true", help="覆盖已存在数据")
    parser.add_argument("--project-only", action="store_true", help="只创建项目")
    parser.add_argument("--no-cases", action="store_true", help="不创建测试用例")
    parser.add_argument("--owner", default="tpm", help="创建者用户 ID (默认: tpm)")
    parser.add_argument("--reviewer", default="reviewer", help="审核人用户 ID (默认: reviewer)")
    args = parser.parse_args()

    # ── 连接数据库 ──
    settings = get_settings()
    client = AsyncMongoClient(settings.mongodb.uri)
    db = client[settings.mongodb.db_name]

    # 注册所有需要的 Document 模型
    await init_beanie(
        database=db,
        document_models=[
            "app.modules.auth.repository.models.rbac.UserDoc",
            "app.modules.project.repository.models.project.ProjectDoc",
            "app.modules.test_specs.repository.models.requirement.TestRequirementDoc",
            "app.modules.test_specs.repository.models.test_case.TestCaseDoc",
            "app.modules.execution_plan.repository.models.execution_plan.ExecutionPlanDoc",
            "app.modules.execution_plan.repository.models.execution_plan.ExecutionPlanItemDoc",
        ],
    )

    # 验证用户存在
    owner = await UserDoc.find_one(UserDoc.user_id == args.owner)
    if not owner:
        print(f"✗ 用户 '{args.owner}' 不存在，请先执行 scripts/init/seed_test_users.py")
        sys.exit(1)
    reviewer = await UserDoc.find_one(UserDoc.user_id == args.reviewer) or owner

    print("=" * 60)
    print("  DML v4 模拟数据生成器")
    print(f"  创建者: {owner.user_id} ({owner.username})")
    print(f"  审核人: {reviewer.user_id} ({reviewer.username})")
    print(f"  重置: {'是' if args.reset else '否'}")
    print("=" * 60)

    # ── 创建数据 ──
    project_map = await create_projects(owner.user_id, args.reset)

    if not args.project_only:
        await create_requirements(owner.user_id, project_map, args.reset)
        if not args.no_cases:
            await create_test_cases(owner.user_id, reviewer.user_id, project_map, args.reset)
        await create_execution_plans(owner.user_id, args.reset)

    print("\n" + "=" * 60)
    print("  完成！")
    print("=" * 60)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
