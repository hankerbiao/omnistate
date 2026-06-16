#!/usr/bin/env python3
"""
模拟测试用例生成脚本

向 dmlv4 后端 API 发送请求，批量创建测试用例。
用于验证测试用例创建流程，或生成演示/测试数据。

用法:
  python scripts/generate_mock_test_cases.py                              # 默认参数创建全部用例
  python scripts/generate_mock_test_cases.py --count 5                    # 只创建 5 条
  python scripts/generate_mock_test_cases.py --user admin --password xxx  # 指定用户登录
  python scripts/generate_mock_test_cases.py --url http://localhost:8000 --req-id TR-2026-00001

依赖:
  pip install httpx
"""

import argparse
import sys
import time
from typing import Any

try:
    import httpx
except ImportError:
    print("需要 httpx 库: pip install httpx")
    sys.exit(1)


# =========================================================================
# 测试用例模板
# =========================================================================
# 每条模板为: (标题后缀, 优先级, 测试分类, 风险等级, 前置条件, 后置条件, 标签, 是否破坏性, 预估时长秒, 环境要求)
# 最终标题格式: "{需求标题} - {标题后缀}"

TEST_CASE_TEMPLATES: list[tuple[str, ...]] = [
    # ========== 功能测试 ==========
    ("正向流程-正常输入-功能验证",
     "P0", "功能测试", "低",
     "系统处于就绪状态，所有依赖服务正常运行",
     "操作成功，数据正确写入数据库，日志记录完整",
     ["冒烟测试", "P0回归", "功能测试"], False, 180, {}),

    ("异常流程-无效输入-错误处理验证",
     "P1", "功能测试", "中",
     "系统处于就绪状态",
     "系统返回明确的错误提示，不产生脏数据",
     ["异常测试", "功能测试"], False, 120, {}),

    ("边界值测试-最大长度输入-稳定性验证",
     "P2", "功能测试", "中",
     "系统处于就绪状态，准备边界值测试数据",
     "系统正确处理边界值输入，无崩溃或数据截断异常",
     ["边界测试", "功能测试"], False, 300, {}),

    ("幂等性验证-重复提交-数据一致性",
     "P2", "功能测试", "低",
     "系统处于就绪状态",
     "重复提交不产生重复数据，返回已有结果",
     ["幂等测试", "功能测试"], False, 90, {}),

    # ========== 性能测试 ==========
    ("并发测试-多用户同时操作-系统负载验证",
     "P1", "性能测试", "高",
     "准备并发测试环境，监控工具就绪",
     "系统在并发下响应时间符合 SLA，无死锁或数据竞争",
     ["性能测试", "并发测试"], False, 600,
     {"并发用户数": 100, "期望响应时间_ms": 2000}),

    ("长时间运行测试-持续运行72小时-稳定性验证",
     "P2", "性能测试", "高",
     "系统部署完成，监控告警配置就绪",
     "系统持续运行正常，无内存泄漏，无性能衰减",
     ["性能测试", "稳定性测试"], False, 3600,
     {"运行时长_hours": 72, "监控指标": ["CPU", "内存", "磁盘IO"]}),

    # ========== 兼容性测试 ==========
    ("跨平台兼容性-不同操作系统-功能一致性",
     "P1", "兼容性测试", "中",
     "准备多操作系统测试环境",
     "各平台功能表现一致，UI 显示正常",
     ["兼容性测试", "跨平台"], False, 600,
     {"操作系统": ["Windows 11", "Ubuntu 22.04", "CentOS 8"]}),

    # ========== 可靠性与异常测试 ==========
    ("掉电恢复测试-异常断电-数据完整性",
     "P1", "可靠性测试", "高",
     "系统正在执行关键操作，准备模拟掉电工具",
     "恢复后系统状态一致，未丢失已持久化数据",
     ["可靠性测试", "异常测试"], True, 900, {}),

    ("网络中断测试-链路断开-自动重连",
     "P2", "可靠性测试", "中",
     "系统正在运行，网络连接正常",
     "网络恢复后自动重连，业务自动续跑，无数据丢失",
     ["可靠性测试", "网络测试"], False, 300,
     {"网络工具": "tc", "中断时长_sec": 30}),

    # ========== 安全测试 ==========
    ("权限验证-越权访问-访问控制检查",
     "P0", "安全测试", "高",
     "准备不同权限级别的测试账号",
     "未授权用户无法访问越权资源，返回 403",
     ["安全测试", "权限测试"], False, 180,
     {"测试角色": ["无权限用户", "低权限用户"]}),

    ("注入攻击-SQL/命令注入-安全防护验证",
     "P1", "安全测试", "高",
     "准备注入测试 payload 列表",
     "系统正确过滤恶意输入，不执行注入命令",
     ["安全测试", "渗透测试"], False, 300,
     {"注入类型": ["SQL", "NoSQL", "命令注入"]}),

    # ========== 配置与环境测试 ==========
    ("配置变更验证-参数修改-系统行为正确性",
     "P2", "配置测试", "中",
     "系统正常运行，准备配置变更方案",
     "配置变更后系统按预期行为运行，配置持久化正确",
     ["配置测试"], False, 240,
     {"涉及配置项": ["数据库连接", "超时设置", "日志级别"]}),
]


def build_payload(template: tuple, req_id: str, req_title: str, index: int) -> dict[str, Any]:
    """根据模板构建测试用例请求体。"""
    suffix, priority, category, risk, pre_cond, post_cond, tags, destructive, duration, env = template

    title = f"{req_title} - {suffix}"

    return {
        "ref_req_id": req_id,
        "title": title,
        "priority": priority,
        "test_category": category,
        "risk_level": risk,
        "pre_condition": pre_cond,
        "post_condition": post_cond,
        "tags": tags,
        "is_destructive": destructive,
        "estimated_duration_sec": duration,
        "required_env": env,
        "is_active": True,
        # 可选: 填写则使用指定用户，不填则后端自动使用当前登录用户
        # "owner_id": "test_dev",
        # "reviewer_id": "test_reviewer",
    }


# =========================================================================
# API 交互
# =========================================================================


def login(client: httpx.Client, base_url: str, user_id: str, password: str) -> str:
    """登录并获取 JWT token。"""
    resp = client.post(
        f"{base_url}/api/v1/auth/login",
        json={"user_id": user_id, "password": password},
    )
    if resp.status_code != 200:
        print(f"  ✗ 登录失败 ({resp.status_code}): {resp.text}")
        sys.exit(1)
    data = resp.json()["data"]
    print(f"  ✓ 登录成功 (用户: {data['user']['user_id']}, 角色: {data['user'].get('role_ids', [])})")
    return data["access_token"]


def get_requirements(client: httpx.Client, base_url: str) -> list[dict[str, Any]]:
    """获取已有需求列表。"""
    resp = client.get(f"{base_url}/api/v1/requirements")
    resp.raise_for_status()
    return resp.json()["data"]


def create_test_case(client: httpx.Client, base_url: str, payload: dict) -> dict:
    """创建一个测试用例，返回结果。"""
    resp = client.post(
        f"{base_url}/api/v1/test-cases",
        json=payload,
    )
    if resp.status_code == 201:
        case = resp.json()["data"]
        return {"success": True, "case_id": case["case_id"], "status": case.get("status", "N/A"), "title": case["title"]}
    else:
        return {"success": False, "status_code": resp.status_code, "error": resp.text, "title": payload.get("title", "")}


# =========================================================================
# 主逻辑
# =========================================================================


def main():
    parser = argparse.ArgumentParser(
        description="生成模拟测试用例 - 向 dmlv4 后端批量创建测试用例",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  %(prog)s                                          # 默认参数创建全部用例\n"
            "  %(prog)s --count 5                                # 只创建 5 条\n"
            "  %(prog)s --user admin --password xxx              # 指定用户登录\n"
            "  %(prog)s --url http://10.17.154.252:8000          # 指定后端地址\n"
            "  %(prog)s --req-id TR-2026-00001                   # 关联到指定需求\n"
            "  %(prog)s --dry-run                                # 预览不实际创建\n"
        ),
    )
    parser.add_argument("--url", default="http://localhost:8000", help="后端 API 地址 (默认: http://localhost:8000)")
    parser.add_argument("--user", default="test_admin", help="登录用户 ID (默认: test_admin)")
    parser.add_argument("--password", default="Admin@123", help="登录密码 (默认: Admin@123)")
    parser.add_argument("--count", type=int, default=None, help="创建条数 (默认: 全部模板)")
    parser.add_argument("--req-id", help="关联的需求 req_id (默认: 使用第一个找到的需求)")
    parser.add_argument("--dry-run", action="store_true", help="只预览不创建")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    client = httpx.Client(timeout=60, base_url=base_url)

    try:
        # ---- 步骤 1: 登录 ----
        print("=" * 60)
        print(f"  dmlv4 模拟测试用例生成器")
        print("=" * 60)

        print(f"\n[1/3] 登录 {base_url} ...")
        token = login(client, base_url, args.user, args.password)
        client.headers["Authorization"] = f"Bearer {token}"

        # ---- 步骤 2: 获取需求 ----
        print(f"\n[2/3] 获取需求列表 ...")
        requirements = get_requirements(client, base_url)
        print(f"  找到 {len(requirements)} 个需求")

        if not requirements:
            print("  ✗ 数据库中没有需求，请先创建一个需求！")
            print("    接口: POST {}/api/v1/requirements".format(base_url))
            print('    示例: curl -X POST {}/api/v1/requirements \\'.format(base_url))
            print('            -H "Authorization: Bearer <token>" \\')
            print('            -H "Content-Type: application/json" \\')
            print('            -d \'{"title": "测试需求", "priority": "P1"}\'')
            sys.exit(1)

        # 选择需求
        if args.req_id:
            req = next((r for r in requirements if r["req_id"] == args.req_id), None)
            if not req:
                print(f"  ✗ 未找到需求 {args.req_id}，可用需求:")
                for r in requirements:
                    print(f"     - {r['req_id']}: {r['title']}")
                sys.exit(1)
        else:
            req = requirements[0]
        req_id = req["req_id"]
        req_title = req.get("title", "(无标题)")
        print(f"  使用需求: {req_id} - {req_title}")

        # ---- 步骤 3: 生成并创建测试用例 ----
        templates = TEST_CASE_TEMPLATES[:args.count] if args.count else TEST_CASE_TEMPLATES

        print(f"\n[3/3] 准备创建 {len(templates)} 个测试用例 ...")
        print(f"  需求 ID: {req_id}")

        if args.dry_run:
            print("\n" + "-" * 60)
            print("  DRY RUN 模式 - 预览内容")
            print("-" * 60)
            for i, tmpl in enumerate(templates, 1):
                payload = build_payload(tmpl, req_id, req_title, i)
                print(f"\n  [{i:02d}] {payload['title']}")
                print(f"       优先级: {payload['priority']}  分类: {payload['test_category']}  风险: {payload['risk_level']}")
                print(f"       标签: {', '.join(payload['tags'])}")
                print(f"       前置条件: {payload['pre_condition'][:60]}...")
                print(f"       后置条件: {payload['post_condition'][:60]}...")
                if payload["is_destructive"]:
                    print("       ⚠  破坏性测试")
            print("\n" + "-" * 60)
            print(f"  共 {len(templates)} 条，未实际创建。去掉 --dry-run 执行。")
            sys.exit(0)

        # 逐条创建
        success_count = 0
        fail_count = 0
        errors: list[dict] = []

        print(f"\n  开始创建 ({len(templates)} 条)...")
        print("-" * 60)

        for i, tmpl in enumerate(templates, 1):
            payload = build_payload(tmpl, req_id, req_title, i)
            result = create_test_case(client, base_url, payload)

            if result["success"]:
                success_count += 1
                print(f"  ✓ [{i:02d}/{len(templates)}] {result['case_id']} | {result['title'][:50]}")
            else:
                fail_count += 1
                errors.append(result)
                print(f"  ✗ [{i:02d}/{len(templates)}] {result['title'][:50]}")
                print(f"      错误 ({result['status_code']}): {result['error'][:200]}")

            # 小间隔避免激进度
            time.sleep(0.3)

        # ---- 结果汇总 ----
        print("\n" + "=" * 60)
        print("  创建完成")
        print("=" * 60)
        print(f"  总  数: {len(templates)}")
        print(f"  成  功: {success_count}")
        print(f"  失  败: {fail_count}")

        if fail_count > 0:
            print(f"\n  失败详情:")
            for err in errors:
                print(f"    - {err['title'][:50]}: HTTP {err['status_code']}")

        print("")

    except httpx.ConnectError:
        print(f"\n  ✗ 无法连接到 {base_url}，请确认后端服务已启动。")
        print(f"    启动方式: python -m app.main")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ✗ 执行出错: {e}")
        raise


if __name__ == "__main__":
    main()
