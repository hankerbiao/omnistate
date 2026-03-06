#!/usr/bin/env python3
"""
DMLV4 执行进度回传SDK - 基础使用示例

本示例展示如何使用SDK的基本功能，包括：
1. 初始化客户端
2. 上报任务状态
3. 上报用例进度
4. 上报步骤结果
5. 清理资源
"""

import time
from datetime import datetime

from dmlv4_execution_sdk import (
    ExecutionReporter,
    ReporterConfig,
    TaskStatus,
    CaseStatus,
    StepStatus,
)


def main():
    """主函数示例"""
    print("=== DMLV4 执行进度回传SDK - 基础使用示例 ===\n")

    # 1. 配置客户端
    print("1. 配置SDK客户端...")
    config = ReporterConfig(
        base_url="http://localhost:8000/api/v1",
        framework_id="example_framework",
        secret="your-secret-key",
        timeout_sec=30.0,
        max_retries=3,
    )

    # 2. 初始化Reporter
    print("2. 初始化Reporter...")
    reporter = ExecutionReporter(config)

    # 示例任务信息
    task_id = "ET-2026-000001"
    external_task_id = "FW-example-123"
    case_id = "TC-2026-001"

    try:
        # 3. 上报任务开始执行
        print("3. 上报任务开始执行...")
        reporter.report_task_status(
            task_id=task_id,
            external_task_id=external_task_id,
            status=TaskStatus.RUNNING.value,
            seq=1,
            detail={"started_at": datetime.now().isoformat()},
        )
        time.sleep(1)  # 模拟处理时间

        # 4. 上报用例开始
        print("4. 上报用例开始执行...")
        reporter.start_case(task_id=task_id, case_id=case_id, seq=2)
        time.sleep(0.5)

        # 5. 上报用例进度
        print("5. 上报用例进度更新...")
        reporter.update_case_progress(
            task_id=task_id,
            case_id=case_id,
            progress_percent=25.0,
            seq=3
        )
        time.sleep(0.5)

        reporter.update_case_progress(
            task_id=task_id,
            case_id=case_id,
            progress_percent=50.0,
            seq=4
        )
        time.sleep(0.5)

        # 6. 上报步骤结果
        print("6. 上报步骤执行结果...")

        # 步骤1 - 通过
        reporter.report_step_result(
            task_id=task_id,
            case_id=case_id,
            step_id="step_01",
            status=StepStatus.PASSED.value,
            seq=5,
            started_at=datetime.now(),
            finished_at=datetime.now(),
            message="步骤1执行通过"
        )
        time.sleep(0.3)

        # 步骤2 - 失败
        reporter.report_step_result(
            task_id=task_id,
            case_id=case_id,
            step_id="step_02",
            status=StepStatus.FAILED.value,
            seq=6,
            started_at=datetime.now(),
            finished_at=datetime.now(),
            message="步骤2执行失败：电压阈值检查失败",
            artifacts=[
                {"type": "log", "path": "/logs/step_02.log"},
                {"type": "screenshot", "path": "/screenshots/step_02.png"}
            ]
        )
        time.sleep(0.3)

        # 7. 上报用例完成
        print("7. 上报用例执行完成...")
        reporter.complete_case(
            task_id=task_id,
            case_id=case_id,
            status=CaseStatus.FAILED.value,
            seq=7,
            message="用例执行失败：步骤2未通过"
        )
        time.sleep(0.5)

        # 8. 发送心跳
        print("8. 发送心跳...")
        reporter.heartbeat(task_id=task_id, seq=8)
        time.sleep(0.2)

        # 9. 上报汇总信息
        print("9. 上报任务汇总...")
        reporter.summary(
            task_id=task_id,
            overall_status=TaskStatus.FAILED.value,
            seq=9,
            totals={
                "total_cases": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "execution_time": "00:02:30"
            }
        )

        print("\n✅ 所有进度信息已上报完成！")

    except Exception as e:
        print(f"\n❌ 上报过程中发生错误: {e}")
        raise

    finally:
        # 10. 清理资源
        print("\n10. 清理资源...")
        try:
            # 等待所有请求发送完成
            reporter.flush(timeout_sec=10.0)
            print("✅ 等待发送完成")

            # 关闭Reporter
            reporter.close()
            print("✅ Reporter已关闭")

        except Exception as e:
            print(f"⚠️  关闭过程中发生错误: {e}")


def demo_task_management():
    """演示任务管理功能（需要实际API支持）"""
    print("\n=== 任务管理功能演示 ===")

    config = ReporterConfig(
        base_url="http://localhost:8000/api/v1",
        framework_id="example_framework",
        secret="your-secret-key",
    )

    reporter = ExecutionReporter(config)

    try:
        # 获取任务详情
        print("获取任务详情...")
        # task = reporter.get_task("ET-2026-000001")
        # print(f"任务信息: {task}")

        # 查询任务列表
        print("查询任务列表...")
        # tasks = reporter.list_tasks(framework="pytest", limit=10)
        # print(f"找到 {len(tasks)} 个任务")

        print("任务管理功能演示完成（API调用需要实际后端服务）")

    except NotImplementedError:
        print("任务管理功能尚未实现（需要API支持）")
    except Exception as e:
        print(f"任务管理演示出错: {e}")


def demo_error_handling():
    """演示错误处理"""
    print("\n=== 错误处理演示 ===")

    # 测试无效配置
    try:
        invalid_config = ReporterConfig(
            base_url="",  # 空URL
            framework_id="",
            secret="",
        )
        print("❌ 应该抛出配置错误")
    except Exception as e:
        print(f"✅ 正确捕获配置错误: {e}")

    # 测试无效状态
    try:
        config = ReporterConfig(
            base_url="http://localhost:8000/api/v1",
            framework_id="test",
            secret="secret"
        )
        reporter = ExecutionReporter(config)

        reporter.report_task_status(
            task_id="test",
            external_task_id=None,
            status="INVALID_STATUS",  # 无效状态
            seq=1
        )
        print("❌ 应该抛出状态错误")
    except Exception as e:
        print(f"✅ 正确捕获状态错误: {e}")


if __name__ == "__main__":
    # 运行基础示例
    main()

    # 演示任务管理
    demo_task_management()

    # 演示错误处理
    demo_error_handling()

    print("\n🎉 所有示例演示完成！")