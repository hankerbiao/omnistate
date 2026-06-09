#!/usr/bin/env python3
"""
执行计划模拟数据种子脚本

通过 API 或直连 MongoDB 推送模拟数据，用于测试执行计划页面和 My Tasks 模块。

用法:
  # dev_bypass_auth 模式（config.yaml 中已开启免认证）
  python seed_execution_plans.py

  # 登录获取 Token（config.yaml 未开启免认证时用）
  python seed_execution_plans.py --login dev_admin:Test@123

  # 直连 MongoDB 模式（最可靠，跳过 API 鉴权）
  python seed_execution_plans.py --direct-db

  # 指定后端地址
  python seed_execution_plans.py --url http://10.0.1.5:8000

前置条件:
  - API 模式：后端服务已运行
  - direct-db 模式：MongoDB 可达（从 config.yaml 读取连接信息）
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    print("❌ 请安装 httpx: pip install httpx")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
#  种子数据定义
# ═══════════════════════════════════════════════════════════════════

USERS = [
    {"user_id": "dev_admin", "username": "管理员"},
    {"user_id": "zhangwei", "username": "张伟"},
    {"user_id": "lina", "username": "李娜"},
    {"user_id": "wanghao", "username": "王浩"},
]

COMPONENTS = {
    "mem": "内存验证组",
    "fw": "固件验证组",
    "tool": "工具链组",
    "storage": "存储验证组",
    "platform": "平台质量组",
}

PLANS: List[Dict[str, Any]] = [
    {
        "title": "Sprint 3 · 安全与兼容性验证",
        "description": "Sprint 3 周期的全面安全测试与固件兼容性验证，覆盖固件升级、权限管理、跨版本兼容等核心场景。",
        "status": "active",
        "start_date": "2026-05-25",
        "end_date": "2026-06-12",
        "items": [
            {"case_id": "TC-003", "ref_type": "auto", "component": "fw", "assignee_id": "zhangwei", "status": "running"},
            {"case_id": "TC-004", "ref_type": "manual", "component": "fw", "assignee_id": "lina", "status": "pending"},
            {"case_id": "TC-009", "ref_type": "auto", "component": "platform", "assignee_id": "wanghao", "status": "done"},
            {"case_id": "TC-010", "ref_type": "manual", "component": "platform", "assignee_id": "zhangwei", "status": "done"},
            {"case_id": "TC-001", "ref_type": "auto", "component": "mem", "assignee_id": "lina", "status": "pending"},
            {"case_id": "TC-005", "ref_type": "auto", "component": "tool", "assignee_id": "wanghao", "status": "done"},
            {"case_id": "TC-015", "ref_type": "auto", "component": "fw", "assignee_id": "zhangwei", "status": "fail"},
            {"case_id": "TC-012", "ref_type": "manual", "component": "fw", "assignee_id": "lina", "status": "pending"},
        ],
    },
    {
        "title": "内存子系统回归测试",
        "description": "内存模块全量回归，含读写压力、边界值、DDR4 兼容性验证。",
        "status": "active",
        "start_date": "2026-06-01",
        "end_date": "2026-06-10",
        "items": [
            {"case_id": "TC-001", "ref_type": "auto", "component": "mem", "assignee_id": "zhangwei", "status": "done"},
            {"case_id": "TC-002", "ref_type": "manual", "component": "mem", "assignee_id": "zhangwei", "status": "done"},
            {"case_id": "TC-011", "ref_type": "auto", "component": "mem", "assignee_id": "lina", "status": "running"},
            {"case_id": "TC-013", "ref_type": "auto", "component": "storage", "assignee_id": "lina", "status": "pending"},
        ],
    },
    {
        "title": "固件升级专项测试",
        "description": "针对 F/W 2.5 版本升级与回滚的专项验证，含跨版本兼容与断电恢复。",
        "status": "draft",
        "start_date": "2026-06-10",
        "end_date": "2026-06-20",
        "trigger_at": "2026-06-15T09:00:00",
        "items": [
            {"case_id": "TC-003", "ref_type": "auto", "component": "fw", "assignee_id": "lina", "status": "pending"},
            {"case_id": "TC-004", "ref_type": "manual", "component": "fw", "assignee_id": "zhangwei", "status": "pending"},
            {"case_id": "TC-015", "ref_type": "auto", "component": "fw", "assignee_id": "wanghao", "status": "pending"},
        ],
    },
    {
        "title": "平台稳定性长稳测试",
        "description": "72 小时长稳压测，含多用户并发、存储性能基准、分布式通信。",
        "status": "done",
        "start_date": "2026-05-20",
        "end_date": "2026-05-28",
        "items": [
            {"case_id": "TC-009", "ref_type": "auto", "component": "platform", "assignee_id": "zhangwei", "status": "done"},
            {"case_id": "TC-007", "ref_type": "auto", "component": "storage", "assignee_id": "lina", "status": "done"},
            {"case_id": "TC-013", "ref_type": "auto", "component": "storage", "assignee_id": "wanghao", "status": "done"},
            {"case_id": "TC-014", "ref_type": "manual", "component": "tool", "assignee_id": "zhangwei", "status": "done"},
        ],
    },
]

RESULT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "TC-001": {
        "passed": True, "notes": "压力 100MB/s 持续 30min 无异常", "severity": "normal",
        "actual": "通过", "expected": "通过", "env": "staging",
        "actual_duration": "30", "attachments": ["/reports/mem_stress_20260601.pdf"],
    },
    "TC-002": {
        "passed": True, "notes": "边界值 ±1 校验通过", "severity": "normal",
        "actual": "通过", "expected": "通过", "env": "staging",
        "actual_duration": "15",
    },
    "TC-004": {
        "passed": False, "notes": "异常断电后固件无法自动恢复，需人工介入", "severity": "critical",
        "actual": "恢复失败", "expected": "30s 内自动恢复", "env": "testing",
        "bug_id": "BUG-2026-0042", "actual_duration": "60",
    },
    "TC-005": {
        "passed": True, "notes": "CI/CD 管道全流程通过", "severity": "normal",
        "actual": "通过", "expected": "通过", "env": "dev",
        "actual_duration": "20",
    },
    "TC-007": {
        "passed": True, "notes": "顺序读 5GB/s, 随机写 2.1GB/s", "severity": "normal",
        "actual": "通过", "expected": "顺序读 ≥4GB/s, 随机写 ≥1.5GB/s", "env": "staging",
        "actual_duration": "40", "attachments": ["/reports/storage_bench_20260522.xlsx"],
    },
    "TC-009": {
        "passed": True, "notes": "50 并发用户同时操作，响应 <200ms", "severity": "normal",
        "actual": "通过", "expected": "通过", "env": "testing",
        "actual_duration": "35",
    },
    "TC-010": {
        "passed": True, "notes": "权限校验全部 26 条通过", "severity": "high",
        "actual": "通过", "expected": "通过", "env": "testing",
        "actual_duration": "20",
    },
    "TC-013": {
        "passed": True, "notes": "16 节点集群通信延迟 <5ms", "severity": "normal",
        "actual": "通过", "expected": "节点间延迟 <10ms", "env": "staging",
        "actual_duration": "60",
    },
    "TC-014": {
        "passed": True, "notes": "工具链部署验证完成", "severity": "normal",
        "actual": "通过", "expected": "通过", "env": "dev",
        "actual_duration": "30",
    },
    "TC-015": {
        "passed": False, "notes": "跨版本回滚失败：2.4→2.3 不兼容", "severity": "critical",
        "actual": "回滚失败", "expected": "成功回滚", "env": "testing",
        "bug_id": "BUG-2026-0045", "actual_duration": "35",
    },
}

# ═══════════════════════════════════════════════════════════════════
#  API 客户端
# ═══════════════════════════════════════════════════════════════════

class ApiClient:
    def __init__(self, base_url: str, token: str | None = None):
        self.base = f"{base_url.rstrip('/')}/api/v1"
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.client = httpx.Client(timeout=30.0, headers=headers)

    def close(self):
        self.client.close()

    def _req(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base}{path}"
        resp = self.client.request(method, url, **kwargs)

        if resp.status_code == 401:
            print(f"\n{'⚠️' * 20}")
            print(f"❌ 鉴权失败（401）: {method} {url}")
            print(f"\n可选修复方案:")
            print(f"  1. 在 config.yaml 中设置 app.dev_bypass_auth: true 后重启后端")
            print(f"  2. 使用 --login user_id:password 参数（如 --login dev_admin:Test@123）")
            print(f"  3. 使用 --direct-db 直连 MongoDB 写入（无需后端鉴权）")
            print(f"{'⚠️' * 20}\n")
            sys.exit(1)

        try:
            data = resp.json()
        except Exception:
            print(f"  ⚠️  响应非 JSON: {resp.status_code} {resp.text[:200]}")
            return {"code": -1, "message": resp.text}

        if resp.status_code >= 400 or data.get("code", 0) != 0:
            detail = data.get("message") or data.get("detail") or data.get("error") or str(data)
            print(f"  ❌ {method} {url} → {resp.status_code} {detail}")
            return data
        return data

    def login(self, user_id: str, password: str) -> str:
        """登录并返回 JWT token"""
        resp = self._req("POST", "/auth/login", json={"user_id": user_id, "password": password})
        token = resp.get("data", {}).get("access_token")
        if not token:
            print(f"❌ 登录失败: user_id={user_id}, 请检查密码是否正确")
            sys.exit(1)
        self.client.headers["Authorization"] = f"Bearer {token}"
        print(f"🔑 登录成功: {user_id} (token 前 8 位: {token[:8]}...)")
        return token

    def create_plan(self, plan: Dict[str, Any]) -> Optional[str]:
        payload = {
            "title": plan["title"],
            "description": plan.get("description", ""),
            "status": plan.get("status", "draft"),
            "start_date": plan.get("start_date"),
            "end_date": plan.get("end_date"),
            "trigger_at": plan.get("trigger_at"),
        }
        print(f"  → 创建计划: {payload['title']}")
        resp = self._req("POST", "/execution-plans/plans", json=payload)
        if resp.get("data") and resp["data"].get("plan_id"):
            plan_id = resp["data"]["plan_id"]
            print(f"    ✅ plan_id={plan_id}")
            return plan_id
        print(f"    ❌ 创建失败: {resp}")
        return None

    def add_items(self, plan_id: str, items: List[Dict[str, Any]]) -> bool:
        print(f"  → 添加 {len(items)} 个条目到 {plan_id}")
        resp = self._req("POST", f"/execution-plans/plans/{plan_id}/items", json={"items": items})
        if resp.get("data"):
            print(f"    ✅ 添加成功")
            return True
        print(f"    ❌ 添加失败: {resp}")
        return False

    def update_item_status(self, plan_id: str, item_id: str, status: str) -> bool:
        resp = self._req("PUT", f"/execution-plans/plans/{plan_id}/items/{item_id}", json={"status": status})
        return bool(resp.get("data"))

    def submit_result(self, item_id: str, result: Dict[str, Any]) -> bool:
        print(f"  → 提交结果: item_id={item_id}, passed={result.get('passed')}")
        resp = self._req("POST", f"/execution-plans/items/{item_id}/result", json=result)
        if resp.get("data"):
            print(f"    ✅ 结果提交成功")
            return True
        print(f"    ❌ 提交失败: {resp}")
        return False

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        resp = self._req("GET", f"/execution-plans/plans/{plan_id}")
        return resp.get("data")

    def verify_linkage(self, assignee_id: str) -> List[Dict[str, Any]]:
        resp = self._req("GET", f"/execution-plans/items/my-items?assignee_id={assignee_id}")
        data = resp.get("data", [])
        if not isinstance(data, list):
            print(f"  ⚠️  响应 data 不是列表 (type={type(data).__name__}), 跳过验证")
            return []
        return data


# ═══════════════════════════════════════════════════════════════════
#  Direct MongoDB 模式 — 跳过 API 和鉴权，直接写库
# ═══════════════════════════════════════════════════════════════════

async def seed_via_mongodb():
    """直连 MongoDB，用 Beanie Document 模型写入种子数据。"""
    from beanie import init_beanie
    from pymongo import AsyncMongoClient

    from app.shared.config.settings import get_settings

    settings = get_settings()
    db_name = settings.mongodb.db_name
    uri = settings.mongodb.uri

    print(f"🔗 连接 MongoDB: {uri}/{db_name}")
    client = AsyncMongoClient(uri)
    database = client[db_name]

    from app.modules.execution_plan.repository.models import (
        DOCUMENT_MODELS as EP_MODELS,
    )

    await init_beanie(database=database, document_models=list(EP_MODELS))

    from app.modules.execution_plan.repository.models import (
        ExecutionPlanDoc, ExecutionPlanItemDoc, ManualExecutionResultDoc,
    )

    total_items = 0

    for p_idx, plan_def in enumerate(PLANS, 1):
        print(f"\n[{p_idx}/{len(PLANS)}] {plan_def['title']}")

        year = datetime.now().year
        seq = p_idx
        plan_id = f"EP-{year}-{str(seq).zfill(6)}"

        plan_doc = ExecutionPlanDoc(
            plan_id=plan_id,
            title=plan_def["title"],
            description=plan_def.get("description", ""),
            status=plan_def.get("status", "draft"),
            start_date=plan_def.get("start_date"),
            end_date=plan_def.get("end_date"),
            trigger_at=plan_def.get("trigger_at"),
            created_by="dev_admin",
        )
        await plan_doc.insert()
        print(f"  ✅ 已创建计划: {plan_id}")

        for i_idx, item in enumerate(plan_def["items"]):
            item_seq = (p_idx * 100) + i_idx + 1
            item_id = f"EPI-{year}-{str(item_seq).zfill(6)}"

            item_doc = ExecutionPlanItemDoc(
                item_id=item_id,
                plan_id=plan_id,
                ref_type=item["ref_type"],
                case_id=item["case_id"],
                case_title=f"测试用例 {item['case_id']}",
                component=item.get("component", ""),
                assignee_id=item.get("assignee_id"),
                status=item.get("status", "pending"),
                order_no=i_idx,
            )
            await item_doc.insert()

            # 已完成条目 → 写结果
            if item["status"] == "done" and item["case_id"] in RESULT_TEMPLATES:
                rst = RESULT_TEMPLATES[item["case_id"]]
                result_seq = (p_idx * 100) + i_idx + 1
                result_id = f"MER-{year}-{str(result_seq).zfill(6)}"
                result_doc = ManualExecutionResultDoc(
                    result_id=result_id,
                    item_id=item_id,
                    plan_id=plan_id,
                    case_id=item["case_id"],
                    passed=rst["passed"],
                    notes=rst.get("notes", ""),
                    severity=rst.get("severity", "normal"),
                    actual=rst.get("actual", ""),
                    expected=rst.get("expected", ""),
                    env=rst.get("env", ""),
                    test_data=rst.get("test_data", ""),
                    bug_id=rst.get("bug_id", ""),
                    actual_duration=rst.get("actual_duration", ""),
                    attachments=rst.get("attachments", []),
                    executed_by=item["assignee_id"] or "dev_admin",
                )
                await result_doc.insert()
                item_doc.result_id = result_id
                await item_doc.save()

        # 重新计算进度
        all_items = await ExecutionPlanItemDoc.find(
            ExecutionPlanItemDoc.plan_id == plan_id,
            ExecutionPlanItemDoc.is_deleted == False,
        ).to_list()
        item_count = len(all_items)
        done_count = sum(1 for it in all_items if it.status == "done")
        progress = round(done_count / item_count * 100) if item_count else 0
        plan_doc.item_count = item_count
        plan_doc.done_count = done_count
        plan_doc.progress_percent = progress
        if item_count > 0 and done_count == item_count:
            plan_doc.status = "done"
        await plan_doc.save()

        total_items += item_count
        print(f"     {item_count} 个条目, {done_count} 已完成")

    await client.close()
    return total_items


# ═══════════════════════════════════════════════════════════════════
#  API 模式执行逻辑
# ═══════════════════════════════════════════════════════════════════

def _find_item_id(plan_data: Dict[str, Any], case_id: str) -> Optional[str]:
    for item in plan_data.get("items", []):
        if item.get("case_id") == case_id:
            return item.get("item_id")
    return None


def seed_via_api(api: ApiClient) -> int:
    total_items = 0

    print(f"\n{'='*60}")
    print(f"📦 开始通过 API 创建执行计划种子数据")
    print(f"{'='*60}\n")

    for p_idx, plan_def in enumerate(PLANS, 1):
        print(f"\n[{p_idx}/{len(PLANS)}] {plan_def['title']}")
        print(f"   ├ 状态: {plan_def.get('status')}")
        print(f"   ├ 周期: {plan_def.get('start_date','-')} → {plan_def.get('end_date','-')}")
        print(f"   └ 条目: {len(plan_def['items'])} 个")

        plan_id = api.create_plan(plan_def)
        if not plan_id:
            continue

        # Step 1: 添加条目（去掉 status，因为创建时不允许传 status）
        items_for_create = []
        for item in plan_def["items"]:
            items_for_create.append({
                "ref_type": item["ref_type"],
                "case_id": item["case_id"],
                "assignee_id": item.get("assignee_id"),
                "component": item.get("component", ""),
            })
        api.add_items(plan_id, items_for_create)
        total_items += len(items_for_create)

        # Step 2: 获取 plan detail，找到 item_id 映射
        plan_detail = api.get_plan(plan_id)
        if not plan_detail:
            continue

        # case_id → item_id 映射
        case_to_item = {}
        for pi in plan_detail.get("items", []):
            case_to_item[pi.get("case_id")] = pi.get("item_id")

        # Step 3: 处理非 pending 状态 → 更新状态 + 提交结果
        for item in plan_def["items"]:
            status = item.get("status", "pending")
            if status in ("pending",):
                continue

            item_id = case_to_item.get(item["case_id"])
            if not item_id:
                print(f"  ⚠️  未找到 item_id for {item['case_id']}")
                continue

            # 更新状态
            print(f"  → 更新 {item['case_id']} 状态为 {status}")
            api.update_item_status(plan_id, item_id, status)

            # 已完成条目 → 提交结果回填
            if status == "done":
                result_template = RESULT_TEMPLATES.get(item["case_id"])
                if result_template:
                    api.submit_result(item_id, result_template)

    print(f"\n{'='*60}")
    print(f"✅ 种子数据创建完成！共创建 {len(PLANS)} 个计划, {total_items} 个条目")
    print(f"{'='*60}\n")
    return total_items


def verify_linkage(api: ApiClient):
    print(f"\n{'='*60}")
    print(f"🔗 验证 My Tasks 联动")
    print(f"{'='*60}\n")
    for user in USERS:
        items = api.verify_linkage(user["user_id"])
        if not items:
            print(f"  👤 {user['username']} ({user['user_id']}): 无计划任务")
            continue
        pending = sum(1 for i in items if isinstance(i, dict) and i.get("status") in ("pending", "running"))
        done = sum(1 for i in items if isinstance(i, dict) and i.get("status") in ("done", "fail"))
        print(f"  👤 {user['username']} ({user['user_id']}): {len(items)} 个任务")
        print(f"     ├ 待处理: {pending}")
        print(f"     └ 已完成: {done}")


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="执行计划种子数据脚本 — 通过 API 或直连 MongoDB 推送模拟数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python seed_execution_plans.py                                          # dev_bypass_auth 模式
  python seed_execution_plans.py --login dev_admin:Test@123               # 登录模式
  python seed_execution_plans.py --direct-db                              # 直连 MongoDB
  python seed_execution_plans.py --url http://10.0.1.5:8000 --login admin:admin123
        """,
    )
    parser.add_argument("--url", default="http://localhost:8000",
                        help="后端 API 基础 URL（默认 http://localhost:8000）")
    parser.add_argument("--login", metavar="user_id:password",
                        help="使用账号密码登录获取 Token，如 dev_admin:Test@123")
    parser.add_argument("--direct-db", action="store_true",
                        help="直连 MongoDB 写入数据（跳过 API 鉴权）")
    return parser.parse_args()


def main():
    args = parse_args()

    # ── 模式 C: 直连 MongoDB ──
    if args.direct_db:
        print("🔧 使用 direct-db 模式: 直连 MongoDB 写入种子数据\n")
        try:
            total = asyncio.run(seed_via_mongodb())
        except Exception as e:
            print(f"\n❌ direct-db 模式执行失败: {e}")
            print("  可能的原因: MongoDB 未启动 / config.yaml 连接信息不正确 / beanie 未安装")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"✅ direct-db 模式完成！共创建 {len(PLANS)} 个计划, {total} 个条目")
        print(f"🎉 启动后端后，在「测试执行计划」和「我的任务」页面即可看到数据")
        print(f"{'='*60}\n")
        return

    # ── 健康检查 ──
    print(f"🔍 检查后端服务: {args.url}")
    try:
        r = httpx.get(f"{args.url.rstrip('/')}/health", timeout=5)
        print(f"   {'✅ 服务正常' if r.status_code < 400 else '⚠️ 服务异常'} (status={r.status_code})")
    except Exception as e:
        print(f"   ❌ 无法连接: {e}")
        print("\n请先启动后端服务:")
        print("  cd backend && uvicorn app.main:app --reload")
        sys.exit(1)

    # ── 模式 A/B: API 模式 ──
    api = ApiClient(args.url)

    try:
        # 模式 B: 登录获取 Token
        if args.login:
            if ":" not in args.login:
                print("❌ --login 格式错误，请使用 user_id:password 格式，如 dev_admin:Test@123")
                sys.exit(1)
            user_id, password = args.login.split(":", 1)
            api.login(user_id, password)
        else:
            print("🔓 使用 dev_bypass_auth 免认证模式")
            print("   如需登录，请使用 --login user_id:password")

        seed_via_api(api)
        verify_linkage(api)

    finally:
        api.close()


if __name__ == "__main__":
    main()
