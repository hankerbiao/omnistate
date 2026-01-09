"""
CPU 模块 Mock 测试用例
用于验证 Allure 报告装饰器展示
"""
import allure
import pytest


@allure.feature("CPU Information")
@allure.story("CPU Information Collection")
@allure.severity(allure.severity_level.NORMAL)
@allure.description("测试 CPU 信息采集功能，验证 Redfish API 和系统命令两种方式")
@allure.epic("Hardware Module Tests")
@allure.parent_suite("Server Hardware Tests")
@allure.suite("CPU Module")
class TestCPUInfoMock:
    """CPU 信息采集 Mock 测试"""

    @pytest.mark.smoke
    @allure.title("采集 CPU 基本信息 - Redfish API")
    @allure.testcase("TC-CPU-MOCK-001", "验证 Redfish API 返回 CPU 核心数和频率")
    @allure.issue("https://jira.company.com/REQ-CPU-001", name="需求: CPU基础信息采集")
    @allure.description("需求ID: REQ-CPU-001 - 通过 Redfish API 采集 CPU 基本信息")
    def test_collect_cpu_via_redfish_mock(self):
        """Mock 测试：Redfish API 采集 CPU 信息"""
        with allure.step("模拟 Redfish API 调用"):
            # Mock 数据
            mock_response = {
                "Processors": [
                    {"Id": "CPU1", "Name": "Intel Xeon Gold 5218", "MaxSpeedMHz": 3200, "Cores": 16},
                    {"Id": "CPU2", "Name": "Intel Xeon Gold 5218", "MaxSpeedMHz": 3200, "Cores": 16}
                ]
            }
            allure.attach(
                str(mock_response),
                name="Mock Redfish Response",
                attachment_type=allure.attachment_type.JSON
            )

        with allure.step("验证 CPU 数据"):
            assert len(mock_response["Processors"]) == 2
            assert mock_response["Processors"][0]["Cores"] == 16
            allure.attach(
                "CPU cores validation passed",
                name="Validation Result",
                attachment_type=allure.attachment_type.TEXT
            )

    @pytest.mark.smoke
    @allure.title("采集 CPU 核心数和频率 - 系统命令")
    @allure.testcase("TC-CPU-MOCK-002", "验证 lscpu 命令返回 CPU 信息")
    @allure.issue("https://jira.company.com/REQ-CPU-002", name="需求: 系统命令采集")
    def test_collect_cpu_via_system_mock(self):
        """Mock 测试：系统命令采集 CPU 信息"""
        mock_output = """Architecture:        x86_64
CPU(s):              32
Model name:          Intel(R) Xeon(R) Gold 5218 CPU @ 2.30GHz
CPU max MHz:         3200.0000
CPU min MHz:         1000.0000
Thread(s) per core:  2"""

        allure.attach(
            mock_output,
            name="Mock lscpu Output",
            attachment_type=allure.attachment_type.TEXT
        )

        # 解析验证
        assert "x86_64" in mock_output
        assert "Intel(R) Xeon" in mock_output

        allure.attach(
            "CPU system info validation passed",
            name="Validation Result",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("CPU Status")
@allure.story("CPU Temperature Monitoring")
@allure.severity(allure.severity_level.CRITICAL)
@allure.description("测试 CPU 温度监控功能，确保温度在正常范围内")
class TestCPUTemperatureMock:
    """CPU 温度监控 Mock 测试"""

    @pytest.mark.status_monitor
    @allure.title("CPU 温度状态检查")
    @allure.testcase("TC-CPU-TEMP-001", "验证 CPU 温度是否超过阈值")
    @allure.issue("https://jira.company.com/REQ-MON-001", name="监控需求: CPU温度")
    def test_cpu_temperature_mock(self):
        """Mock 测试：CPU 温度监控"""
        # Mock 传感器数据
        mock_sensors = {
            "CPU_1_Temp": {"value": "45", "unit": "degreesC", "status": "OK"},
            "CPU_2_Temp": {"value": "47", "unit": "degreesC", "status": "OK"},
            "PCH_Temp": {"value": "42", "unit": "degreesC", "status": "OK"}
        }

        allure.attach(
            str(mock_sensors),
            name="Temperature Sensor Data",
            attachment_type=allure.attachment_type.JSON
        )

        # 温度验证
        max_temp_threshold = 90
        for sensor, data in mock_sensors.items():
            temp = int(data["value"])
            assert temp < max_temp_threshold, f"{sensor} temperature {temp} exceeds threshold {max_temp_threshold}"

        allure.attach(
            "All temperatures are within normal range",
            name="Status Check Result",
            attachment_type=allure.attachment_type.TEXT
        )