#!/usr/bin/env python3
"""验证测试数据脚本。

用法：
python scripts/verify_test_data.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

from beanie import init_beanie
from pymongo import AsyncMongoClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.db.config import settings
from app.modules.test_specs.repository.models import TestRequirementDoc, TestCaseDoc


def format_datetime(dt) -> str:
    """格式化日期时间"""
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return 'N/A'


async def verify_requirements():
    """验证测试需求数据"""
    print("=" * 80)
    print("📋 测试需求数据详情")
    print("=" * 80)

    requirements = await TestRequirementDoc.find_all().to_list()

    for idx, req in enumerate(requirements, 1):
        print(f"\n[{idx}] 需求: {req.req_id}")
        print(f"  标题: {req.title}")
        print(f"  描述: {req.description[:100]}..." if req.description and len(req.description) > 100 else f"  描述: {req.description}")
        print(f"  优先级: {req.priority}")
        print(f"  状态: {req.status}")
        print(f"  TPM负责人: {req.tpm_owner_id}")
        print(f"  手工执行负责人: {req.manual_dev_id or 'N/A'}")
        print(f"  自动化负责人: {req.auto_dev_id or 'N/A'}")
        print(f"  目标组件: {', '.join(req.target_components)}")
        print(f"  关键参数: {len(req.key_parameters)} 个")
        for param in req.key_parameters:
            print(f"    - {param.get('key', 'N/A')}: {param.get('value', 'N/A')}")
        print(f"  技术规格: {req.technical_spec[:80] if req.technical_spec else 'N/A'}...")
        print(f"  风险点: {req.risk_points[:80] if req.risk_points else 'N/A'}...")
        print(f"  创建时间: {format_datetime(req.created_at)}")
        print(f"  更新时间: {format_datetime(req.updated_at)}")


async def verify_test_cases():
    """验证测试用例数据"""
    print("\n\n" + "=" * 80)
    print("🧪 测试用例数据详情")
    print("=" * 80)

    test_cases = await TestCaseDoc.find_all().to_list()

    for idx, case in enumerate(test_cases, 1):
        print(f"\n[{idx}] 用例: {case.case_id}")
        print(f"  标题: {case.title}")
        print(f"  关联需求: {case.ref_req_id}")
        print(f"  版本: {case.version}")
        print(f"  状态: {case.status}")
        print(f"  优先级: {case.priority or 'N/A'}")
        print(f"  所有者: {case.owner_id or 'N/A'}")
        print(f"  评审人: {case.reviewer_id or 'N/A'}")
        print(f"  测试分类: {case.test_category or 'N/A'}")
        print(f"  预估时长: {case.estimated_duration_sec or 'N/A'} 秒")
        print(f"  目标组件: {', '.join(case.target_components)}")
        print(f"  标签: {', '.join(case.tags)}")
        print(f"  破坏性测试: {'是' if case.is_destructive else '否'}")
        print(f"  需要自动化: {'是' if case.is_need_auto else '否'}")
        print(f"  自动化类型: {case.automation_type or 'N/A'}")
        print(f"  风险等级: {case.risk_level or 'N/A'}")
        print(f"  保密级别: {case.confidentiality or 'N/A'}")
        print(f"  可见范围: {case.visibility_scope or 'N/A'}")
        print(f"  环境要求:")
        for key, value in case.required_env.items():
            if isinstance(value, list):
                print(f"    - {key}: {', '.join(value)}")
            else:
                print(f"    - {key}: {value}")
        print(f"  前置条件: {case.pre_condition[:80] if case.pre_condition else 'N/A'}...")
        print(f"  后置条件: {case.post_condition[:80] if case.post_condition else 'N/A'}...")
        print(f"  测试步骤: {len(case.steps)} 个")
        for step in case.steps:
            print(f"    - {step.step_id}: {step.name}")
            print(f"      操作: {step.action[:60]}...")
            print(f"      预期: {step.expected[:60]}...")
        print(f"  创建时间: {format_datetime(case.created_at)}")
        print(f"  更新时间: {format_datetime(case.updated_at)}")


async def verify_relationships():
    """验证需求与用例的关联关系"""
    print("\n\n" + "=" * 80)
    print("🔗 需求与用例关联关系")
    print("=" * 80)

    requirements = await TestRequirementDoc.find_all().to_list()

    for req in requirements:
        cases = await TestCaseDoc.find(TestCaseDoc.ref_req_id == req.req_id).to_list()
        print(f"\n📋 需求: {req.req_id} - {req.title}")
        print(f"  状态: {req.status} | 优先级: {req.priority}")
        if cases:
            print(f"  关联用例: {len(cases)} 个")
            for case in cases:
                print(f"    - {case.case_id}: {case.title} (状态: {case.status})")
        else:
            print(f"  ⚠️  该需求暂无关联用例")


async def show_statistics():
    """显示数据统计"""
    print("\n\n" + "=" * 80)
    print("📊 数据统计")
    print("=" * 80)

    # 总数统计
    total_reqs = await TestRequirementDoc.find_all().count()
    total_cases = await TestCaseDoc.find_all().count()

    print(f"\n📈 总量统计:")
    print(f"  测试需求总数: {total_reqs}")
    print(f"  测试用例总数: {total_cases}")
    print(f"  用例/需求比例: {total_cases/total_reqs:.2f}" if total_reqs > 0 else "  用例/需求比例: N/A")

    # 按状态统计
    req_status_stats = {}
    case_status_stats = {}
    priority_stats = {}
    component_stats = {}

    reqs = await TestRequirementDoc.find_all().to_list()
    for req in reqs:
        # 状态统计
        status = req.status
        req_status_stats[status] = req_status_stats.get(status, 0) + 1

        # 优先级统计
        priority = req.priority
        priority_stats[priority] = priority_stats.get(priority, 0) + 1

        # 组件统计
        for component in req.target_components:
            component_stats[component] = component_stats.get(component, 0) + 1

    cases = await TestCaseDoc.find_all().to_list()
    for case in cases:
        # 状态统计
        status = case.status
        case_status_stats[status] = case_status_stats.get(status, 0) + 1

    print(f"\n📋 需求状态分布:")
    for status, count in sorted(req_status_stats.items()):
        print(f"  {status}: {count} ({count/total_reqs*100:.1f}%)")

    print(f"\n🧪 用例状态分布:")
    for status, count in sorted(case_status_stats.items()):
        print(f"  {status}: {count} ({count/total_cases*100:.1f}%)")

    print(f"\n🎯 优先级分布:")
    for priority, count in sorted(priority_stats.items()):
        print(f"  {priority}: {count} ({count/total_reqs*100:.1f}%)")

    print(f"\n🖥️  目标组件统计:")
    for component, count in sorted(component_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {component}: {count} 次")


async def main():
    """主函数"""
    client = AsyncMongoClient(settings.MONGO_URI)
    try:
        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[TestRequirementDoc, TestCaseDoc],
        )

        await verify_requirements()
        await verify_test_cases()
        await verify_relationships()
        await show_statistics()

        print("\n\n" + "=" * 80)
        print("✅ 验证完成！")
        print("=" * 80)

    finally:
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


if __name__ == "__main__":
    asyncio.run(main())