#!/usr/bin/env python3
"""
DMLV4 执行进度回传SDK - 命令行工具

提供命令行接口，方便测试和调试SDK功能。
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional

from . import ExecutionReporter, AsyncExecutionReporter, ReporterConfig
from .models import TaskStatus, CaseStatus, StepStatus


def create_reporter_config(args) -> ReporterConfig:
    """创建Reporter配置"""
    return ReporterConfig(
        base_url=args.base_url or os.getenv("DMLV4_BASE_URL", "http://localhost:8000/api/v1"),
        framework_id=args.framework_id or os.getenv("DMLV4_FRAMEWORK_ID", "cli-tool"),
        secret=args.secret or os.getenv("DMLV4_SECRET"),
        timeout_sec=getattr(args, 'timeout', 30.0),
        max_retries=getattr(args, 'retries', 3),
    )


def cmd_task_status(args):
    """上报任务状态命令"""
    config = create_reporter_config(args)
    reporter = ExecutionReporter(config)

    try:
        reporter.report_task_status(
            task_id=args.task_id,
            external_task_id=getattr(args, 'external_id', None),
            status=args.status,
            seq=args.seq,
            detail=json.loads(args.detail) if args.detail else None,
        )
        print(f"✅ 任务状态已上报: {args.task_id} -> {args.status}")
    except Exception as e:
        print(f"❌ 上报失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        reporter.close()


def cmd_case_status(args):
    """上报用例状态命令"""
    config = create_reporter_config(args)
    reporter = ExecutionReporter(config)

    try:
        reporter.report_case_status(
            task_id=args.task_id,
            case_id=args.case_id,
            status=args.status,
            seq=args.seq,
            progress_percent=args.progress,
            step_total=args.step_total,
            step_passed=args.step_passed,
            step_failed=args.step_failed,
            step_skipped=args.step_skipped,
        )
        print(f"✅ 用例状态已上报: {args.case_id} -> {args.status}")
    except Exception as e:
        print(f"❌ 上报失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        reporter.close()


def cmd_step_result(args):
    """上报步骤结果命令"""
    config = create_reporter_config(args)
    reporter = ExecutionReporter(config)

    try:
        started_at = datetime.fromisoformat(args.started_at) if args.started_at else None
        finished_at = datetime.fromisoformat(args.finished_at) if args.finished_at else None

        reporter.report_step_result(
            task_id=args.task_id,
            case_id=args.case_id,
            step_id=args.step_id,
            status=args.status,
            seq=args.seq,
            started_at=started_at,
            finished_at=finished_at,
            message=args.message,
            artifacts=json.loads(args.artifacts) if args.artifacts else None,
        )
        print(f"✅ 步骤结果已上报: {args.step_id} -> {args.status}")
    except Exception as e:
        print(f"❌ 上报失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        reporter.close()


def cmd_heartbeat(args):
    """发送心跳命令"""
    config = create_reporter_config(args)
    reporter = ExecutionReporter(config)

    try:
        reporter.heartbeat(task_id=args.task_id, seq=args.seq)
        print(f"✅ 心跳已发送: {args.task_id}")
    except Exception as e:
        print(f"❌ 发送失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        reporter.close()


def cmd_summary(args):
    """发送汇总命令"""
    config = create_reporter_config(args)
    reporter = ExecutionReporter(config)

    try:
        totals = json.loads(args.totals) if args.totals else {}
        reporter.summary(
            task_id=args.task_id,
            overall_status=args.status,
            seq=args.seq,
            totals=totals
        )
        print(f"✅ 汇总信息已发送: {args.task_id} -> {args.status}")
    except Exception as e:
        print(f"❌ 发送失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        reporter.close()


def cmd_demo(args):
    """演示命令"""
    config = create_reporter_config(args)
    reporter = ExecutionReporter(config)

    try:
        task_id = args.task_id
        print(f"🎬 开始演示SDK功能 (任务: {task_id})")

        # 1. 上报任务开始
        print("1. 上报任务开始...")
        reporter.report_task_status(
            task_id=task_id,
            external_task_id="CLI-DEMO-001",
            status=TaskStatus.RUNNING.value,
            seq=1,
            detail={"demo": True, "started_by": "cli-tool"}
        )

        # 2. 上报用例
        case_id = "DEMO-TESTCASE-001"
        print(f"2. 上报用例: {case_id}")
        reporter.start_case(task_id, case_id, seq=2)

        # 3. 上报进度
        print("3. 上报进度...")
        reporter.update_case_progress(task_id, case_id, 25.0, seq=3)
        reporter.update_case_progress(task_id, case_id, 75.0, seq=4)

        # 4. 上报步骤
        print("4. 上报步骤结果...")
        reporter.report_step_result(
            task_id=task_id,
            case_id=case_id,
            step_id="step-01",
            status=StepStatus.PASSED.value,
            seq=5,
            message="步骤1: 数据准备"
        )
        reporter.report_step_result(
            task_id=task_id,
            case_id=case_id,
            step_id="step-02",
            status=StepStatus.PASSED.value,
            seq=6,
            message="步骤2: 业务逻辑执行"
        )

        # 5. 完成用例
        print("5. 完成用例...")
        reporter.complete_case(
            task_id=task_id,
            case_id=case_id,
            status=CaseStatus.PASSED.value,
            seq=7,
            message="所有步骤执行成功"
        )

        # 6. 发送心跳
        print("6. 发送心跳...")
        reporter.heartbeat(task_id, seq=8)

        # 7. 发送汇总
        print("7. 发送汇总...")
        reporter.summary(
            task_id=task_id,
            overall_status=TaskStatus.PASSED.value,
            seq=9,
            totals={
                "total_cases": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "demo": True
            }
        )

        print("✅ 演示完成！")

    except Exception as e:
        print(f"❌ 演示失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        reporter.close()


def create_parser():
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        prog="dmlv4-reporter",
        description="DMLV4 执行进度回传SDK - 命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 上报任务状态
  dmlv4-reporter task-status --task-id ET-2026-000001 --status RUNNING --seq 1

  # 上报用例状态
  dmlv4-reporter case-status --task-id ET-2026-000001 --case-id TEST-001 --status PASSED --seq 2

  # 发送心跳
  dmlv4-reporter heartbeat --task-id ET-2026-000001 --seq 1

  # 运行演示
  dmlv4-reporter demo --task-id ET-2026-000001

环境变量:
  DMLV4_BASE_URL     API基础地址 (默认: http://localhost:8000/api/v1)
  DMLV4_FRAMEWORK_ID 框架标识 (默认: cli-tool)
  DMLV4_SECRET       签名密钥 (必需)

使用前请确保设置 DMLV4_SECRET 环境变量。
        """
    )

    # 全局参数
    parser.add_argument(
        "--base-url",
        help="DMLV4 API基础地址 (可使用DMLV4_BASE_URL环境变量)"
    )
    parser.add_argument(
        "--framework-id",
        help="框架标识 (可使用DMLV4_FRAMEWORK_ID环境变量)"
    )
    parser.add_argument(
        "--secret",
        help="签名密钥 (可使用DMLV4_SECRET环境变量)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="请求超时时间 (默认: 30秒)"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="最大重试次数 (默认: 3)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 任务状态命令
    task_parser = subparsers.add_parser("task-status", help="上报任务状态")
    task_parser.add_argument("--task-id", required=True, help="任务ID")
    task_parser.add_argument("--external-id", help="外部任务ID")
    task_parser.add_argument("--status", required=True, help="任务状态")
    task_parser.add_argument("--seq", type=int, required=True, help="序列号")
    task_parser.add_argument("--detail", help="详细信息 (JSON格式)")
    task_parser.set_defaults(func=cmd_task_status)

    # 用例状态命令
    case_parser = subparsers.add_parser("case-status", help="上报用例状态")
    case_parser.add_argument("--task-id", required=True, help="任务ID")
    case_parser.add_argument("--case-id", required=True, help="用例ID")
    case_parser.add_argument("--status", required=True, help="用例状态")
    case_parser.add_argument("--seq", type=int, required=True, help="序列号")
    case_parser.add_argument("--progress", type=float, help="进度百分比")
    case_parser.add_argument("--step-total", type=int, help="总步骤数")
    case_parser.add_argument("--step-passed", type=int, help="通过步骤数")
    case_parser.add_argument("--step-failed", type=int, help="失败步骤数")
    case_parser.add_argument("--step-skipped", type=int, help="跳过步骤数")
    case_parser.set_defaults(func=cmd_case_status)

    # 步骤结果命令
    step_parser = subparsers.add_parser("step-result", help="上报步骤结果")
    step_parser.add_argument("--task-id", required=True, help="任务ID")
    step_parser.add_argument("--case-id", required=True, help="用例ID")
    step_parser.add_argument("--step-id", required=True, help="步骤ID")
    step_parser.add_argument("--status", required=True, help="步骤状态")
    step_parser.add_argument("--seq", type=int, required=True, help="序列号")
    step_parser.add_argument("--started-at", help="开始时间 (ISO格式)")
    step_parser.add_argument("--finished-at", help="结束时间 (ISO格式)")
    step_parser.add_argument("--message", help="消息")
    step_parser.add_argument("--artifacts", help="附件信息 (JSON格式)")
    step_parser.set_defaults(func=cmd_step_result)

    # 心跳命令
    heartbeat_parser = subparsers.add_parser("heartbeat", help="发送心跳")
    heartbeat_parser.add_argument("--task-id", required=True, help="任务ID")
    heartbeat_parser.add_argument("--seq", type=int, required=True, help="序列号")
    heartbeat_parser.set_defaults(func=cmd_heartbeat)

    # 汇总命令
    summary_parser = subparsers.add_parser("summary", help="发送汇总信息")
    summary_parser.add_argument("--task-id", required=True, help="任务ID")
    summary_parser.add_argument("--status", required=True, help="总体状态")
    summary_parser.add_argument("--seq", type=int, required=True, help="序列号")
    summary_parser.add_argument("--totals", help="汇总数据 (JSON格式)")
    summary_parser.set_defaults(func=cmd_summary)

    # 演示命令
    demo_parser = subparsers.add_parser("demo", help="运行演示")
    demo_parser.add_argument("--task-id", required=True, help="任务ID")
    demo_parser.set_defaults(func=cmd_demo)

    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 检查必需的环境变量
    config_needed = not any([
        args.secret,
        os.getenv("DMLV4_SECRET")
    ])

    if config_needed and args.command != "demo":
        print("❌ 错误: 需要设置签名密钥", file=sys.stderr)
        print("请设置 DMLV4_SECRET 环境变量或使用 --secret 参数", file=sys.stderr)
        sys.exit(1)

    # 执行命令
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n⚠️  操作被用户中断", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 执行失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()