#!/usr/bin/env python3
"""初始化测试数据脚本。

用途：
- 创建测试需求数据
- 创建测试用例数据
- 关联需求和用例
- 可重复执行，幂等插入

用法：
python scripts/seed_test_data.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any

from beanie import init_beanie
from pymongo import AsyncMongoClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.db.config import settings
from app.modules.test_specs.repository.models import TestRequirementDoc, TestCaseDoc
from app.modules.test_specs.repository.models.test_case import TestCaseStep

# 模拟数据
SAMPLE_REQUIREMENTS = [
    {
        "req_id": "TR-2026-001",
        "title": "DDR5 内存高温压力验证",
        "description": "针对新一代服务器平台的 DDR5 内存进行全面的压力与兼容性验证，确保在高温高负载下的稳定性。重点验证 ECC 错误率、内存带宽衰减和系统稳定性。",
        "technical_spec": "符合 JEDEC DDR5 标准，支持 5600MT/s 速率，工作电压 1.1V，支持 ECC 错误纠正。",
        "target_components": ["Memory", "CPU", "Motherboard"],
        "firmware_version": "BIOS v2.1.0",
        "priority": "P0",
        "key_parameters": [
            {"key": "电压", "value": "1.1V"},
            {"key": "频率", "value": "5600MT/s"},
            {"key": "容量", "value": "128GB"},
            {"key": "ECC", "value": "支持"}
        ],
        "risk_points": "重点验证高温下（85°C）ECC 错误率，需注意不同内存厂商芯片的兼容性差异。",
        "tpm_owner_id": "tpm001",
        "manual_dev_id": "tester001",
        "auto_dev_id": "auto001",
        "status": "用例开发中",
    },
    {
        "req_id": "TR-2026-002",
        "title": "CPU 温度监控精度验证",
        "description": "验证服务器 CPU 在高负载运行时的温度监控传感器准确性和过热保护机制。",
        "technical_spec": "支持 Intel Xeon Scalable 3rd Gen，温度范围 25°C - 105°C，精度 ±2°C。",
        "target_components": ["CPU", "Thermal Sensor", "BMC"],
        "firmware_version": "BMC v3.2.1",
        "priority": "P1",
        "key_parameters": [
            {"key": "温度范围", "value": "25°C - 105°C"},
            {"key": "精度", "value": "±2°C"},
            {"key": "告警阈值", "value": "85°C"}
        ],
        "risk_points": "需注意不同 CPU 型号的温度特性差异，传感器校准精度。",
        "tpm_owner_id": "tpm001",
        "manual_dev_id": "tester001",
        "auto_dev_id": "auto001",
        "status": "待指派",
    },
    {
        "req_id": "TR-2026-003",
        "title": "NVMe SSD 峰值性能测试",
        "description": "验证 NVMe SSD 在不同工作负载下的峰值性能和稳定性。",
        "technical_spec": "支持 PCIe 4.0 x4，顺序读取速度 ≥7000MB/s，顺序写入速度 ≥5000MB/s。",
        "target_components": ["Storage", "Motherboard", "CPU"],
        "firmware_version": "BIOS v2.1.0",
        "priority": "P1",
        "key_parameters": [
            {"key": "接口", "value": "PCIe 4.0 x4"},
            {"key": "顺序读速", "value": "≥7000MB/s"},
            {"key": "顺序写速", "value": "≥5000MB/s"},
            {"key": "容量", "value": "2TB"}
        ],
        "risk_points": "需验证长时间高负载下的性能衰减和温度控制。",
        "tpm_owner_id": "tpm001",
        "manual_dev_id": "qa001",
        "auto_dev_id": "auto001",
        "status": "用例开发中",
    },
    {
        "req_id": "TR-2026-004",
        "title": "GPU 渲染性能基准测试",
        "description": "评估 GPU 在 AI 推理和图形渲染场景下的性能表现。",
        "technical_spec": "支持 CUDA 12.0，FP16 性能 ≥500 TFLOPS，显存带宽 ≥900 GB/s。",
        "target_components": ["GPU", "CPU", "Memory"],
        "firmware_version": "BIOS v2.1.0",
        "priority": "P2",
        "key_parameters": [
            {"key": "CUDA版本", "value": "12.0"},
            {"key": "FP16性能", "value": "≥500 TFLOPS"},
            {"key": "显存带宽", "value": "≥900 GB/s"},
            {"key": "显存容量", "value": "80GB"}
        ],
        "risk_points": "功耗和散热管理，长时间高负载稳定性。",
        "tpm_owner_id": "tpm001",
        "manual_dev_id": "dev001",
        "auto_dev_id": "auto001",
        "status": "待指派",
    },
    {
        "req_id": "TR-2026-005",
        "title": "网络适配器延迟测试",
        "description": "测试 100GbE 网络适配器的端到端延迟和吞吐量。",
        "technical_spec": "支持 IEEE 802.3bs，延迟 ≤0.5μs，吞吐量 ≥95Gbps。",
        "target_components": ["Network", "CPU", "Motherboard"],
        "firmware_version": "BIOS v2.1.0",
        "priority": "P2",
        "key_parameters": [
            {"key": "速率", "value": "100GbE"},
            {"key": "延迟", "value": "≤0.5μs"},
            {"key": "吞吐量", "value": "≥95Gbps"},
            {"key": "协议", "value": "RoCE v2"}
        ],
        "risk_points": "网络延迟测试环境隔离，CPU 亲和性配置。",
        "tpm_owner_id": "tpm001",
        "manual_dev_id": "viewer001",
        "auto_dev_id": "auto001",
        "status": "评审中",
    },
]

SAMPLE_TEST_CASES = [
    # DDR5 内存相关用例
    {
        "case_id": "TC-2026-001",
        "ref_req_id": "TR-2026-001",
        "title": "DDR5 内存基本功能验证",
        "version": 1,
        "is_active": True,
        "change_log": "初始版本创建",
        "status": "DRAFT",
        "owner_id": "tester001",
        "reviewer_id": "tpm001",
        "priority": "P0",
        "estimated_duration_sec": 3600,
        "target_components": ["Memory", "CPU"],
        "required_env": {
            "os": "Ubuntu 20.04.6 LTS",
            "firmware": "BIOS v2.1.0",
            "hardware": "Intel Xeon Gold 6348, 128GB DDR5-5600",
            "dependencies": ["MemTest86", "Stress-ng"],
            "tooling": ["dmidecode", "lshw"]
        },
        "tags": ["DDR5", "内存", "基本功能", "P0"],
        "test_category": "FUNCTIONAL",
        "tooling_req": ["内存测试卡", "示波器"],
        "is_destructive": False,
        "pre_condition": "系统已安装 DDR5 内存，BIOS 配置正确，环境温度 25°C",
        "post_condition": "移除所有测试负载，系统恢复正常状态",
        "steps": [
            {
                "step_id": "step-001",
                "name": "系统启动检查",
                "action": "启动系统，使用 dmidecode 检查内存信息",
                "expected": "系统识别所有 128GB DDR5 内存，频率 5600MT/s"
            },
            {
                "step_id": "step-002",
                "name": "运行内存自检",
                "action": "使用 MemTest86 进行 1 轮完整测试",
                "expected": "测试通过，错误数为 0"
            },
            {
                "step_id": "step-003",
                "name": "内存压力测试",
                "action": "使用 Stress-ng 进行 30 分钟压力测试",
                "expected": "系统稳定运行，无崩溃或死机"
            }
        ],
        "is_need_auto": True,
        "is_automated": False,
        "automation_type": "pytest",
        "script_entity_id": "script-ddr5-basic-001",
        "risk_level": "MEDIUM",
        "confidentiality": "INTERNAL",
        "visibility_scope": "PROJECT",
        "attachments": [],
        "custom_fields": {"test_environment": "lab_A", "batch": "batch_001"},
    },
    {
        "case_id": "TC-2026-002",
        "ref_req_id": "TR-2026-001",
        "title": "DDR5 内存高温压力测试",
        "version": 1,
        "is_active": True,
        "change_log": "初始版本创建",
        "status": "DRAFT",
        "owner_id": "tester001",
        "reviewer_id": "tpm001",
        "priority": "P0",
        "estimated_duration_sec": 14400,
        "target_components": ["Memory"],
        "required_env": {
            "os": "Ubuntu 20.04.6 LTS",
            "firmware": "BIOS v2.1.0",
            "hardware": "Intel Xeon Gold 6348, 128GB DDR5-5600",
            "dependencies": ["MemTest86", "Thermal chamber"],
            "tooling": ["温度监控脚本"]
        },
        "tags": ["DDR5", "内存", "高温", "压力测试", "P0"],
        "test_category": "STRESS",
        "tooling_req": ["高温试验箱", "温度传感器"],
        "is_destructive": True,
        "pre_condition": "系统已安装 DDR5 内存，高温试验箱设置至 85°C",
        "post_condition": "系统降至常温，清除测试数据",
        "steps": [
            {
                "step_id": "step-001",
                "name": "环境预热",
                "action": "将系统放入高温试验箱，加热至 85°C",
                "expected": "系统稳定运行，温度保持在 85°C ± 2°C"
            },
            {
                "step_id": "step-002",
                "name": "高温内存测试",
                "action": "在高温环境下运行 MemTest86 连续 4 小时",
                "expected": "ECC 错误率 < 0.001%，无系统崩溃"
            },
            {
                "step_id": "step-003",
                "name": "性能衰减测试",
                "action": "使用 Stress-ng 测试内存带宽衰减",
                "expected": "带宽衰减 < 5%，性能稳定"
            }
        ],
        "is_need_auto": True,
        "is_automated": False,
        "automation_type": "pytest",
        "script_entity_id": "script-ddr5-stress-002",
        "risk_level": "HIGH",
        "confidentiality": "INTERNAL",
        "visibility_scope": "PROJECT",
        "attachments": [],
        "custom_fields": {"test_environment": "lab_A", "batch": "batch_001"},
    },
    # CPU 温度监控相关用例
    {
        "case_id": "TC-2026-003",
        "ref_req_id": "TR-2026-002",
        "title": "CPU 温度传感器精度验证",
        "version": 1,
        "is_active": True,
        "change_log": "初始版本创建",
        "status": "DRAFT",
        "owner_id": "tester001",
        "reviewer_id": "tpm001",
        "priority": "P1",
        "estimated_duration_sec": 7200,
        "target_components": ["CPU", "Thermal Sensor"],
        "required_env": {
            "os": "Ubuntu 20.04.6 LTS",
            "firmware": "BIOS v2.1.0, BMC v3.2.1",
            "hardware": "Intel Xeon Gold 6348",
            "dependencies": ["IPMI tools", "lm-sensors"],
            "tooling": ["高精度温度计", "热电偶"]
        },
        "tags": ["CPU", "温度", "传感器", "精度", "P1"],
        "test_category": "FUNCTIONAL",
        "tooling_req": ["温度校准设备", "热电偶"],
        "is_destructive": False,
        "pre_condition": "CPU 温度传感器已校准，系统空闲",
        "post_condition": "恢复默认温度监控设置",
        "steps": [
            {
                "step_id": "step-001",
                "name": "空闲温度采集",
                "action": "系统空闲状态下读取 CPU 温度（传感器读数 vs 实际测量）",
                "expected": "传感器读数与实际测量差值 ≤ 2°C"
            },
            {
                "step_id": "step-002",
                "name": "负载温度测试",
                "action": "CPU 满负载运行，采集温度数据",
                "expected": "满载温度 ≤ 95°C，监控数据准确"
            },
            {
                "step_id": "step-003",
                "name": "告警阈值验证",
                "action": "设置告警阈值 85°C，触发高温告警",
                "expected": "告警触发及时，日志记录完整"
            }
        ],
        "is_need_auto": True,
        "is_automated": False,
        "automation_type": "pytest",
        "script_entity_id": "script-cpu-temp-003",
        "risk_level": "MEDIUM",
        "confidentiality": "INTERNAL",
        "visibility_scope": "PROJECT",
        "attachments": [],
        "custom_fields": {"test_environment": "lab_B", "batch": "batch_001"},
    },
    # NVMe SSD 相关用例
    {
        "case_id": "TC-2026-004",
        "ref_req_id": "TR-2026-003",
        "title": "NVMe SSD 峰值性能基准测试",
        "version": 1,
        "is_active": True,
        "change_log": "初始版本创建",
        "status": "REVIEW",
        "owner_id": "qa001",
        "reviewer_id": "tpm001",
        "priority": "P1",
        "estimated_duration_sec": 10800,
        "target_components": ["Storage", "Motherboard"],
        "required_env": {
            "os": "Ubuntu 20.04.6 LTS",
            "firmware": "BIOS v2.1.0, NVMe SSD FW v1.0",
            "hardware": "Intel Xeon Gold 6348, PCIe 4.0 x4",
            "dependencies": ["fio", "hdparm"],
            "tooling": ["IOMeter", "CrystalDiskMark"]
        },
        "tags": ["NVMe", "SSD", "性能", "基准测试", "P1"],
        "test_category": "PERFORMANCE",
        "tooling_req": ["高性能 NVMe SSD", "散热片"],
        "is_destructive": False,
        "pre_condition": "NVMe SSD 已安装最新固件，系统已优化",
        "post_condition": "移除测试文件，恢复默认设置",
        "steps": [
            {
                "step_id": "step-001",
                "name": "顺序读取性能",
                "action": "使用 fio 测试顺序读取性能（队列深度 32）",
                "expected": "顺序读取速度 ≥ 7000 MB/s"
            },
            {
                "step_id": "step-002",
                "name": "顺序写入性能",
                "action": "使用 fio 测试顺序写入性能（队列深度 32）",
                "expected": "顺序写入速度 ≥ 5000 MB/s"
            },
            {
                "step_id": "step-003",
                "name": "随机读写性能",
                "action": "使用 fio 测试 4K 随机读写性能",
                "expected": "4K 随机读取 ≥ 1000K IOPS，随机写入 ≥ 800K IOPS"
            }
        ],
        "is_need_auto": True,
        "is_automated": True,
        "automation_type": "pytest",
        "script_entity_id": "script-nvme-perf-004",
        "risk_level": "MEDIUM",
        "confidentiality": "INTERNAL",
        "visibility_scope": "PROJECT",
        "attachments": [],
        "custom_fields": {"test_environment": "lab_C", "batch": "batch_001"},
    },
    # GPU 渲染相关用例
    {
        "case_id": "TC-2026-005",
        "ref_req_id": "TR-2026-004",
        "title": "GPU AI 推理性能测试",
        "version": 1,
        "is_active": True,
        "change_log": "初始版本创建",
        "status": "DRAFT",
        "owner_id": "dev001",
        "reviewer_id": "tpm001",
        "priority": "P2",
        "estimated_duration_sec": 18000,
        "target_components": ["GPU", "Memory"],
        "required_env": {
            "os": "Ubuntu 20.04.6 LTS",
            "firmware": "CUDA 12.0, Driver 535.104.05",
            "hardware": "NVIDIA H100 80GB",
            "dependencies": ["CUDA toolkit", "cuDNN", "PyTorch"],
            "tooling": ["NVIDIA Nsight", "nvidia-smi"]
        },
        "tags": ["GPU", "AI", "推理", "性能", "P2"],
        "test_category": "PERFORMANCE",
        "tooling_req": ["H100 GPU", "高功耗电源"],
        "is_destructive": False,
        "pre_condition": "CUDA 环境已配置，GPU 驱动正常",
        "post_condition": "清理测试模型和缓存",
        "steps": [
            {
                "step_id": "step-001",
                "name": "FP16 推理性能",
                "action": "使用 ResNet-50 模型测试 FP16 推理吞吐量",
                "expected": "推理吞吐量 ≥ 15000 images/sec"
            },
            {
                "step_id": "step-002",
                "name": "显存带宽测试",
                "action": "使用 CUDA 内存带宽测试工具",
                "expected": "显存带宽 ≥ 900 GB/s"
            },
            {
                "step_id": "step-003",
                "name": "长时间稳定性",
                "action": "连续运行 8 小时推理负载",
                "expected": "性能衰减 < 3%，无显存泄漏"
            }
        ],
        "is_need_auto": True,
        "is_automated": False,
        "automation_type": "pytest",
        "script_entity_id": "script-gpu-ai-005",
        "risk_level": "LOW",
        "confidentiality": "INTERNAL",
        "visibility_scope": "PROJECT",
        "attachments": [],
        "custom_fields": {"test_environment": "lab_D", "batch": "batch_002"},
    },
    # 网络适配器相关用例
    {
        "case_id": "TC-2026-006",
        "ref_req_id": "TR-2026-005",
        "title": "100GbE 网络延迟基准测试",
        "version": 1,
        "is_active": True,
        "change_log": "初始版本创建",
        "status": "REVIEW",
        "owner_id": "viewer001",
        "reviewer_id": "tpm001",
        "priority": "P2",
        "estimated_duration_sec": 5400,
        "target_components": ["Network", "CPU"],
        "required_env": {
            "os": "Ubuntu 20.04.6 LTS",
            "firmware": "BIOS v2.1.0, NIC FW v8.45",
            "hardware": "Mellanox ConnectX-6 Dx",
            "dependencies": ["netperf", "iperf3"],
            "tooling": ["网络测试仪", "数据包捕获工具"]
        },
        "tags": ["网络", "100GbE", "延迟", "基准", "P2"],
        "test_category": "PERFORMANCE",
        "tooling_req": ["2 台 100GbE 交换机", "光模块"],
        "is_destructive": False,
        "pre_condition": "网络环境已隔离，CPU 亲和性已配置",
        "post_condition": "恢复默认网络配置",
        "steps": [
            {
                "step_id": "step-001",
                "name": "网络延迟测试",
                "action": "使用 netperf 测试 TCP_RR 延迟",
                "expected": "平均延迟 ≤ 0.5μs，99% < 1μs"
            },
            {
                "step_id": "step-002",
                "name": "吞吐量测试",
                "action": "使用 iperf3 测试 TCP 吞吐量",
                "expected": "吞吐量 ≥ 95 Gbps，利用率 ≥ 95%"
            },
            {
                "step_id": "step-003",
                "name": "CPU 利用率",
                "action": "监控网络传输时的 CPU 利用率",
                "expected": "CPU 利用率 ≤ 20%（无 DPDK 优化）"
            }
        ],
        "is_need_auto": True,
        "is_automated": False,
        "automation_type": "pytest",
        "script_entity_id": "script-100gbe-lat-006",
        "risk_level": "LOW",
        "confidentiality": "INTERNAL",
        "visibility_scope": "PROJECT",
        "attachments": [],
        "custom_fields": {"test_environment": "lab_E", "batch": "batch_002"},
    },
]


async def create_requirements():
    """创建测试需求数据"""
    created_count = 0
    updated_count = 0

    for req_data in SAMPLE_REQUIREMENTS:
        # 检查需求是否已存在
        existing = await TestRequirementDoc.find_one(TestRequirementDoc.req_id == req_data["req_id"])

        if existing:
            # 更新现有需求
            for key, value in req_data.items():
                setattr(existing, key, value)
            await existing.save()
            updated_count += 1
            print(f"✅ 更新需求: {req_data['req_id']} - {req_data['title']}")
        else:
            # 创建新需求
            await TestRequirementDoc(**req_data).insert()
            created_count += 1
            print(f"✅ 创建需求: {req_data['req_id']} - {req_data['title']}")

    return created_count, updated_count


async def create_test_cases():
    """创建测试用例数据"""
    created_count = 0
    updated_count = 0

    for case_data in SAMPLE_TEST_CASES:
        # 处理步骤
        if "steps" in case_data:
            steps = []
            for step_data in case_data["steps"]:
                steps.append(TestCaseStep(**step_data))
            case_data["steps"] = steps

        # 检查用例是否已存在
        existing = await TestCaseDoc.find_one(TestCaseDoc.case_id == case_data["case_id"])

        if existing:
            # 更新现有用例
            for key, value in case_data.items():
                setattr(existing, key, value)
            await existing.save()
            updated_count += 1
            print(f"✅ 更新用例: {case_data['case_id']} - {case_data['title']}")
        else:
            # 创建新用例
            await TestCaseDoc(**case_data).insert()
            created_count += 1
            print(f"✅ 创建用例: {case_data['case_id']} - {case_data['title']}")

    return created_count, updated_count


async def main():
    """主函数"""
    print("=" * 80)
    print("开始初始化测试数据")
    print("=" * 80)

    client = AsyncMongoClient(settings.MONGO_URI)
    try:
        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[TestRequirementDoc, TestCaseDoc],
        )

        # 创建需求数据
        print("\n📋 创建测试需求数据...")
        req_created, req_updated = await create_requirements()

        # 创建用例数据
        print("\n🧪 创建测试用例数据...")
        case_created, case_updated = await create_test_cases()

        # 打印统计信息
        print("\n" + "=" * 80)
        print("数据初始化完成！")
        print("=" * 80)
        print(f"📊 需求统计: 新建 {req_created} 个，更新 {req_updated} 个")
        print(f"📊 用例统计: 新建 {case_created} 个，更新 {case_updated} 个")
        print("=" * 80)

        # 显示数据摘要
        print("\n📈 数据摘要:")
        total_requirements = await TestRequirementDoc.find_all().count()
        total_test_cases = await TestCaseDoc.find_all().count()
        print(f"  总需求数: {total_requirements}")
        print(f"  总用例数: {total_test_cases}")

        # 按状态统计
        req_status_stats = {}
        case_status_stats = {}

        reqs = await TestRequirementDoc.find_all().to_list()
        for req in reqs:
            status = req.status
            req_status_stats[status] = req_status_stats.get(status, 0) + 1

        cases = await TestCaseDoc.find_all().to_list()
        for case in cases:
            status = case.status
            case_status_stats[status] = case_status_stats.get(status, 0) + 1

        print("\n📋 需求状态分布:")
        for status, count in req_status_stats.items():
            print(f"  {status}: {count}")

        print("\n🧪 用例状态分布:")
        for status, count in case_status_stats.items():
            print(f"  {status}: {count}")

        print("\n✅ 数据初始化完成！")

    finally:
        close_result = client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


if __name__ == "__main__":
    asyncio.run(main())