"""
CPU 模块异常场景 Mock 测试用例
"""
import allure
import pytest


@allure.feature("CPU Information")
@allure.story("CPU Exception Scenarios")
@allure.severity(allure.severity_level.CRITICAL)
@allure.description("CPU 异常场景测试：温度过高、核心故障、API 超时等")
class TestCPUExceptionMock:
    """CPU 异常场景 Mock 测试"""

    @allure.title("CPU 温度过高告警")
    @allure.testcase("TC-CPU-EXC-001", "验证 CPU 温度超过阈值时触发告警")
    @allure.issue("https://jira.company.com/BUG-CPU-001", name="BUG: CPU 过热")
    def test_cpu_temperature_over_threshold(self):
        """Mock 测试：CPU 温度超过阈值"""
        # 模拟异常数据 - 温度过高
        mock_sensors = {
            "CPU_1_Temp": {"value": "105", "unit": "degreesC", "threshold_max": "95", "status": "CRITICAL"},
            "CPU_2_Temp": {"value": "98", "unit": "degreesC", "threshold_max": "95", "status": "WARNING"}
        }

        allure.attach(
            str(mock_sensors),
            name="Temperature Sensor Data",
            attachment_type=allure.attachment_type.JSON
        )

        # 异常验证
        for sensor, data in mock_sensors.items():
            temp = int(data["value"])
            threshold = int(data["threshold_max"])

            # 预期：CPU1 应该触发告警
            assert temp > threshold, f"{sensor} temperature {temp} should exceed threshold {threshold}"

        allure.attach(
            "WARNING: CPU1 temperature (105°C) exceeds maximum threshold (95°C)",
            name="Alert Message",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("CPU 核心故障")
    @allure.testcase("TC-CPU-EXC-002", "验证 CPU 核心故障检测")
    def test_cpu_core_failure(self):
        """Mock 测试：CPU 核心故障"""
        mock_cpu_status = {
            "cpu_id": "CPU1",
            "total_cores": 16,
            "enabled_cores": 14,
            "disabled_cores": [13, 14],
            "status": "DEGRADED",
            "health": "WARNING"
        }

        allure.attach(
            str(mock_cpu_status),
            name="CPU Core Status",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证有核心禁用
        assert mock_cpu_status["enabled_cores"] < mock_cpu_status["total_cores"]
        assert mock_cpu_status["status"] == "DEGRADED"

        allure.attach(
            "WARNING: 2 CPU cores are disabled, system running in degraded mode",
            name="Alert Message",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("Redfish API 连接超时")
    @allure.testcase("TC-CPU-EXC-003", "验证 Redfish API 超时处理")
    def test_redfish_api_timeout(self):
        """Mock 测试：Redfish API 超时"""
        mock_error = {
            "error_code": "CONNECT_TIMEOUT",
            "message": "Connection to Redfish API timed out after 30 seconds",
            "endpoint": "/Systems/system/Processors",
            "retry_count": 3
        }

        allure.attach(
            str(mock_error),
            name="API Error Response",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证错误处理
        assert mock_error["error_code"] == "CONNECT_TIMEOUT"

        allure.attach(
            "ERROR: Failed to collect CPU info via Redfish API (timeout)",
            name="Error Summary",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("CPU 频率异常")
    @allure.testcase("TC-CPU-EXC-004", "验证 CPU 频率低于预期")
    def test_cpu_frequency_abnormal(self):
        """Mock 测试：CPU 频率异常（低于标称值）"""
        mock_frequency = {
            "cpu_model": "Intel Xeon Gold 5218",
            "nominal_frequency_mhz": 2300,
            "current_frequency_mhz": 800,
            "turbo_mode": "DISABLED",
            "power_mode": "POWER_SAVING",
            "status": "ABNORMAL"
        }

        allure.attach(
            str(mock_frequency),
            name="CPU Frequency Data",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证频率异常
        assert mock_frequency["current_frequency_mhz"] < mock_frequency["nominal_frequency_mhz"]

        allure.attach(
            "WARNING: CPU is running below nominal frequency (800MHz vs 2300MHz)",
            name="Alert Message",
            attachment_type=allure.attachment_type.TEXT
        )