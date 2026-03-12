#!/usr/bin/env python3
"""
MinIO日志SDK集成示例
演示如何在实际自动化测试脚本中集成使用
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from minio_log_manager import MinioLogManager


def run_automation_test():
    """模拟自动化测试执行过程"""
    print("开始执行自动化测试...")

    # 模拟测试参数
    test_config = {
        "project": "PCIe-Switch-FW",
        "machine_ip": "10.17.154.252",
        "test_plan_id": "TP-20260311-001",
        "test_cases": [
            {"name": "init_test", "duration": 2.3, "result": "PASS"},
            {"name": "data_transfer", "duration": 15.7, "result": "PASS"},
            {"name": "exception_handling", "duration": 30.0, "result": "FAIL"}
        ]
    }

    # 生成测试日志
    log_content = generate_test_log(test_config)
    log_file = write_test_log(log_content)

    # 生成测试报告
    report_content = generate_test_report(test_config)
    report_file = write_test_report(report_content)

    return [log_file, report_file], test_config


def generate_test_log(config):
    """生成测试日志内容"""
    log_lines = []
    log_lines.append("=" * 50)
    log_lines.append("自动化测试执行日志")
    log_lines.append("=" * 50)
    log_lines.append(f"项目名称: {config['project']}")
    log_lines.append(f"测试机器: {config['machine_ip']}")
    log_lines.append(f"测试计划: {config['test_plan_id']}")
    log_lines.append(f"开始时间: 2024-03-11 14:30:00")
    log_lines.append("")

    for case in config['test_cases']:
        log_lines.append(f"测试用例: {case['name']}")
        log_lines.append(f"  执行时间: {case['duration']}秒")
        log_lines.append(f"  测试结果: {case['result']}")
        if case['result'] == 'FAIL':
            log_lines.append(f"  错误信息: 超时异常 - 执行时间超过30秒限制")
        log_lines.append("")

    log_lines.append(f"结束时间: 2024-03-11 14:32:45")

    # 统计结果
    passed = sum(1 for case in config['test_cases'] if case['result'] == 'PASS')
    total = len(config['test_cases'])
    log_lines.append(f"总体结果: {passed}/{total} PASS")

    return "\n".join(log_lines)


def generate_test_report(config):
    """生成测试报告内容"""
    passed = sum(1 for case in config['test_cases'] if case['result'] == 'PASS')
    total = len(config['test_cases'])
    pass_rate = (passed / total * 100) if total > 0 else 0

    return f"""{{
    "project": "{config['project']}",
    "machine_ip": "{config['machine_ip']}",
    "test_plan_id": "{config['test_plan_id']}",
    "execution_time": "2024-03-11 14:30:00 - 2024-03-11 14:32:45",
    "summary": {{
        "total_cases": {total},
        "passed_cases": {passed},
        "failed_cases": {total - passed},
        "pass_rate": {pass_rate:.1f}%
    }},
    "test_cases": {config['test_cases']}
}}"""


def write_test_log(content):
    """写入测试日志文件"""
    filename = "test_execution.log"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return filename


def write_test_report(content):
    """写入测试报告文件"""
    filename = "test_report.json"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return filename


def upload_logs_to_minio(file_list, config):
    """上传日志文件到MinIO"""
    print("开始上传日志文件到MinIO...")

    # 初始化MinIO管理器
    mgr = MinioLogManager(
        endpoint="10.17.154.252:9003",
        access_key="admin",
        secret_key="12345678",
        bucket_name="auto-test-logs",
        secure=False
    )

    # 批量上传文件
    results = mgr.upload_multiple_logs(
        project=config['project'],
        machine_ip=config['machine_ip'],
        test_plan_id=config['test_plan_id'],
        local_file_paths=file_list
    )

    return results


def cleanup_local_files(file_list):
    """清理本地测试文件"""
    print("清理本地测试文件...")
    for filename in file_list:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"  删除: {filename}")


def main():
    """主执行函数"""
    try:
        # 1. 运行自动化测试
        print("=" * 60)
        print("第一步: 执行自动化测试")
        print("=" * 60)
        file_list, config = run_automation_test()

        # 2. 上传日志到MinIO
        print("\n" + "=" * 60)
        print("第二步: 上传日志到MinIO")
        print("=" * 60)
        upload_results = upload_logs_to_minio(file_list, config)

        # 3. 显示上传结果
        print("\n上传结果:")
        for filename, result in upload_results.items():
            if result.startswith("http"):
                print(f"  ✓ {filename}: 上传成功")
                print(f"    下载链接: {result}")
            else:
                print(f"  ✗ {filename}: {result}")

        # 4. 获取项目文件列表
        print("\n" + "=" * 60)
        print("第三步: 获取项目文件列表")
        print("=" * 60)

        mgr = MinioLogManager()
        files = mgr.list_log_files(project=config['project'])
        print(f"{config['project']} 项目的日志文件:")
        for file_info in files:
            print(f"  - {file_info['file_name']} ({file_info['size']} bytes)")

        # 5. 清理本地文件
        print("\n" + "=" * 60)
        print("第四步: 清理本地文件")
        print("=" * 60)
        cleanup_local_files(file_list)

        print("\n自动化测试和日志上传完成!")

    except Exception as e:
        print(f"执行过程中出现错误: {e}")
        # 尝试清理可能残留的文件
        try:
            cleanup_local_files(file_list)
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()