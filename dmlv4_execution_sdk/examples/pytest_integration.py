#!/usr/bin/env python3
"""
DMLV4 执行进度回传SDK - Pytest集成示例

展示如何在pytest测试框架中集成SDK，实现：
1. 自动上报测试用例开始/结束状态
2. 自动上报测试步骤执行结果
3. 测试结果汇总上报
4. 测试环境信息收集
"""

import os
import pytest
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

from dmlv4_execution_sdk import (
    ExecutionReporter,
    ReporterConfig,
    CaseStatus,
    StepStatus,
)


class DMLV4Plugin:
    """pytest插件 - 自动上报测试进度到DMLV4系统"""

    def __init__(self, config: ReporterConfig, task_id: str):
        """初始化插件

        Args:
            config: SDK配置
            task_id: DMLV4任务ID
        """
        self.reporter = ExecutionReporter(config)
        self.task_id = task_id
        self.case_seq = 0
        self.step_seq = 0
        self.test_results = {}
        self.start_time = datetime.now()

        # 收集测试环境信息
        self.env_info = {
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
            "platform": os.sys.platform,
            "pytest_version": pytest.__version__,
            "start_time": self.start_time.isoformat(),
            "cwd": os.getcwd(),
        }

    @pytest.hookimpl(tryfirst=True, hookwrapper=True)
    def pytest_runtest_protocol(self, item, call):
        """pytest测试协议钩子 - 监控每个测试用例的执行"""
        test_name = item.nodeid.replace("::", ".")

        if call.when == "setup":
            # 测试开始
            self.case_seq += 1
            self._log_info(f"开始执行测试用例: {test_name}")
            self.reporter.start_case(
                task_id=self.task_id,
                case_id=test_name,
                seq=self.case_seq
            )

        elif call.when == "call":
            # 测试执行
            try:
                # 执行测试
                outcome = yield
                result = outcome.get_result()

                # 转换pytest结果为DMLV4状态
                if result.passed:
                    status = CaseStatus.PASSED.value
                    message = f"测试通过 ({result.duration:.3f}s)"
                elif result.failed:
                    status = CaseStatus.FAILED.value
                    message = f"测试失败: {result.longrepr}" if result.longrepr else "测试失败"
                elif result.skipped:
                    status = CaseStatus.SKIPPED.value
                    message = f"测试跳过: {result.longrepr}" if result.longrepr else "测试跳过"
                else:
                    status = CaseStatus.ERROR.value
                    message = "未知测试结果"

                # 记录测试结果
                self.test_results[test_name] = {
                    "status": status,
                    "duration": result.duration,
                    "message": message,
                    "when": call.when,
                    "start_time": call.start,
                    "stop_time": call.stop,
                }

                # 上报测试完成
                self.reporter.complete_case(
                    task_id=self.task_id,
                    case_id=test_name,
                    status=status,
                    seq=self.case_seq,
                    message=message
                )

                self._log_info(f"测试用例完成: {test_name} - {status}")

            except Exception as e:
                # 测试执行异常
                error_message = f"测试执行异常: {str(e)}"
                self.test_results[test_name] = {
                    "status": CaseStatus.ERROR.value,
                    "duration": 0,
                    "message": error_message,
                    "traceback": traceback.format_exc(),
                    "when": call.when,
                }

                self.reporter.complete_case(
                    task_id=self.task_id,
                    case_id=test_name,
                    status=CaseStatus.ERROR.value,
                    seq=self.case_seq,
                    message=error_message
                )

                self._log_error(f"测试用例异常: {test_name} - {error_message}")
                raise

        elif call.when == "teardown":
            # 测试清理（可选）
            pass

    def pytest_runtest_makereport(self, item, call):
        """收集测试报告信息（备用钩子）"""
        pass

    def pytest_session_finish(self, session, exitstatus):
        """pytest会话结束钩子 - 上报汇总信息"""
        self._log_info("测试会话结束，开始上报汇总信息")

        # 计算测试统计
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results.values() if r["status"] == CaseStatus.PASSED.value)
        failed_tests = sum(1 for r in self.test_results.values() if r["status"] == CaseStatus.FAILED.value)
        skipped_tests = sum(1 for r in self.test_results.values() if r["status"] == CaseStatus.SKIPPED.value)
        error_tests = sum(1 for r in self.test_results.values() if r["status"] == CaseStatus.ERROR.value)

        # 确定总体状态
        if error_tests > 0:
            overall_status = CaseStatus.ERROR.value
        elif failed_tests > 0:
            overall_status = CaseStatus.FAILED.value
        elif passed_tests > 0 and passed_tests == total_tests:
            overall_status = CaseStatus.PASSED.value
        else:
            overall_status = CaseStatus.SKIPPED.value

        # 计算执行时间
        end_time = datetime.now()
        execution_time = (end_time - self.start_time).total_seconds()

        # 上报汇总信息
        self.reporter.summary(
            task_id=self.task_id,
            overall_status=overall_status,
            seq=self.case_seq + 1,
            totals={
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "error": error_tests,
                "execution_time": f"{execution_time:.3f}s",
                "exit_status": exitstatus,
                "environment": self.env_info,
            }
        )

        self._log_info(f"汇总信息上报完成 - 总体状态: {overall_status}")

    def pytest_configure(self, config):
        """pytest配置钩子"""
        self._log_info("DMLV4 pytest插件配置完成")

    def _log_info(self, message: str):
        """记录信息日志"""
        print(f"[DMLV4-INFO] {datetime.now().isoformat()} - {message}")

    def _log_error(self, message: str):
        """记录错误日志"""
        print(f"[DMLV4-ERROR] {datetime.now().isoformat()} - {message}", file=__import__('sys').stderr)

    def close(self):
        """关闭插件"""
        try:
            self.reporter.flush(timeout_sec=30.0)
            self.reporter.close()
            self._log_info("DMLV4插件已关闭")
        except Exception as e:
            self._log_error(f"关闭插件时发生错误: {e}")


# === pytest fixture 和配置 ===

@pytest.fixture(scope="session")
def dmlv4_reporter():
    """pytest session级别的fixture，提供DMLV4 reporter实例"""
    # 从环境变量读取配置
    base_url = os.getenv("DMLV4_BASE_URL", "http://localhost:8000/api/v1")
    framework_id = os.getenv("DMLV4_FRAMEWORK_ID", "pytest-runner")
    secret = os.getenv("DMLV4_SECRET")
    task_id = os.getenv("DMLV4_TASK_ID")

    if not secret:
        pytest.skip("DMLV4_SECRET环境变量未设置，跳过DMLV4集成测试")
    if not task_id:
        pytest.skip("DMLV4_TASK_ID环境变量未设置，跳过DMLV4集成测试")

    config = ReporterConfig(
        base_url=base_url,
        framework_id=framework_id,
        secret=secret,
        timeout_sec=30.0,
        max_retries=3,
    )

    reporter = ExecutionReporter(config)

    yield reporter

    # 清理
    reporter.flush(timeout_sec=30.0)
    reporter.close()


# === 示例测试用例 ===

class TestDMLV4Integration:
    """示例测试类 - 演示与DMLV4的集成"""

    def test_example_pass(self, dmlv4_reporter):
        """示例测试 - 通过"""
        assert True

    def test_example_fail(self, dmlv4_reporter):
        """示例测试 - 失败"""
        assert False, "这是一个故意失败的测试"

    def test_example_skip(self, dmlv4_reporter):
        """示例测试 - 跳过"""
        pytest.skip("这是一个故意跳过的测试")

    def test_with_steps(self, dmlv4_reporter, task_id="ET-2026-000001"):
        """示例测试 - 包含多个步骤"""
        test_name = "test_with_steps"
        seq = 1

        # 步骤1
        dmlv4_reporter.report_step_result(
            task_id=task_id,
            case_id=test_name,
            step_id="step_01",
            status=StepStatus.RUNNING.value,
            seq=seq,
            started_at=datetime.now(),
            message="执行步骤1"
        )
        time.sleep(0.1)

        # 模拟步骤1执行
        dmlv4_reporter.report_step_result(
            task_id=task_id,
            case_id=test_name,
            step_id="step_01",
            status=StepStatus.PASSED.value,
            seq=seq + 1,
            finished_at=datetime.now(),
            message="步骤1执行成功"
        )
        seq += 2

        # 步骤2
        dmlv4_reporter.report_step_result(
            task_id=task_id,
            case_id=test_name,
            step_id="step_02",
            status=StepStatus.RUNNING.value,
            seq=seq,
            started_at=datetime.now(),
            message="执行步骤2"
        )
        time.sleep(0.1)

        # 模拟步骤2执行失败
        dmlv4_reporter.report_step_result(
            task_id=task_id,
            case_id=test_name,
            step_id="step_02",
            status=StepStatus.FAILED.value,
            seq=seq + 1,
            finished_at=datetime.now(),
            message="步骤2执行失败：断言错误"
        )

        # 整个用例失败
        assert False, "步骤2失败导致整个用例失败"


# === pytest.ini 配置示例 ===

PYTEST_INI_CONTENT = """
[pytest]
# 注册DMLV4插件
addopts = --tb=short
           -v
           --dmlv4-reporter

# 环境变量说明
# DMLV4_BASE_URL: DMLV4系统API地址
# DMLV4_FRAMEWORK_ID: 框架标识
# DMLV4_SECRET: 签名密钥
# DMLV4_TASK_ID: 任务ID

# 使用示例：
# DMLV4_BASE_URL=http://localhost:8000/api/v1 \\
# DMLV4_FRAMEWORK_ID=pytest-runner \\
# DMLV4_SECRET=your-secret-key \\
# DMLV4_TASK_ID=ET-2026-000001 \\
# pytest
"""


def demo_manual_plugin_usage():
    """演示手动使用插件（不通过pytest命令行）"""
    print("\n=== 手动使用DMLV4插件示例 ===")

    # 配置
    config = ReporterConfig(
        base_url="http://localhost:8000/api/v1",
        framework_id="manual_test",
        secret="your-secret-key",
    )

    task_id = "ET-2026-000001"
    plugin = DMLV4Plugin(config, task_id)

    try:
        # 模拟测试执行
        test_cases = [
            "test_manual_case_1",
            "test_manual_case_2",
            "test_manual_case_3"
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"执行测试用例 {i}: {test_case}")

            # 开始测试
            plugin.case_seq += 1
            plugin.reporter.start_case(
                task_id=task_id,
                case_id=test_case,
                seq=plugin.case_seq
            )

            # 模拟测试执行
            time.sleep(0.1)

            # 完成测试
            if i % 3 == 0:  # 每3个测试失败1个
                status = CaseStatus.FAILED.value
                message = f"模拟失败: 测试用例 {test_case}"
            elif i % 2 == 0:  # 偶数测试跳过
                status = CaseStatus.SKIPPED.value
                message = f"模拟跳过: 测试用例 {test_case}"
            else:
                status = CaseStatus.PASSED.value
                message = f"模拟通过: 测试用例 {test_case}"

            plugin.reporter.complete_case(
                task_id=task_id,
                case_id=test_case,
                status=status,
                seq=plugin.case_seq,
                message=message
            )

            print(f"  -> {status}")

        # 模拟会话结束
        plugin.test_results = {
            tc: {"status": CaseStatus.PASSED.value, "duration": 0.1}
            for tc in test_cases
        }

        plugin.pytest_session_finish(None, 0)

        print("✅ 手动插件演示完成")

    finally:
        plugin.close()


if __name__ == "__main__":
    # 运行手动插件演示
    demo_manual_plugin_usage()

    print("\n📝 要在pytest中使用此插件，请：")
    print("1. 将 DMLV4Plugin 类添加到你的 conftest.py 文件中")
    print("2. 配置相应的环境变量")
    print("3. 运行 pytest 命令")

    print("\n📄 pytest.ini 配置示例：")
    print(PYTEST_INI_CONTENT)