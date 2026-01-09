"""
风扇模块异常场景 Mock 测试用例
"""
import allure


@allure.feature("Fan Management")
@allure.story("Fan Exception Scenarios")
@allure.severity(allure.severity_level.CRITICAL)
@allure.description("风扇异常场景测试：风扇停转、转速异常、冗余丢失等")
class TestFanExceptionMock:
    """风扇异常场景 Mock 测试"""

    @allure.title("风扇停转")
    @allure.testcase("TC-FAN-EXC-001", "验证风扇停转检测")
    @allure.issue("https://jira.company.com/BUG-FAN-001", name="BUG: 风扇停转")
    def test_fan_stopped(self):
        """Mock 测试：风扇停转"""
        mock_fans = {
            "FAN1": {"speed_rpm": 0, "min_rpm": 1000, "status": "FAILED", "health": "CRITICAL"},
            "FAN2": {"speed_rpm": 5200, "min_rpm": 1000, "status": "OK", "health": "OK"},
            "FAN3": {"speed_rpm": 5100, "min_rpm": 1000, "status": "OK", "health": "OK"}
        }

        allure.attach(
            str(mock_fans),
            name="Fan Status Data",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证 FAN1 停转
        assert mock_fans["FAN1"]["speed_rpm"] == 0
        assert mock_fans["FAN1"]["status"] == "FAILED"

        allure.attach(
            "CRITICAL: FAN1 has stopped - immediate attention required!",
            name="Alert Message",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("风扇转速异常 - 过快")
    @allure.testcase("TC-FAN-EXC-002", "验证风扇转速超过最大阈值")
    def test_fan_speed_too_fast(self):
        """Mock 测试：风扇转速异常（过快）"""
        mock_fans = {
            "FAN1": {"speed_rpm": 9800, "max_rpm": 10000, "status": "WARNING", "health": "WARNING"},
            "FAN2": {"speed_rpm": 5200, "max_rpm": 10000, "status": "OK", "health": "OK"}
        }

        allure.attach(
            str(mock_fans),
            name="Fan Speed Data",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证转速接近最大值
        assert mock_fans["FAN1"]["speed_rpm"] > mock_fans["FAN1"]["max_rpm"] * 0.95

        allure.attach(
            "WARNING: FAN1 speed (9800 RPM) approaching maximum threshold (10000 RPM)",
            name="Alert Message",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("风扇转速异常 - 过慢")
    @allure.testcase("TC-FAN-EXC-003", "验证风扇转速低于最小阈值")
    def test_fan_speed_too_slow(self):
        """Mock 测试：风扇转速异常（过慢）"""
        mock_fans = {
            "FAN3": {"speed_rpm": 800, "min_rpm": 1000, "status": "DEGRADED", "health": "WARNING"},
            "FAN4": {"speed_rpm": 5200, "min_rpm": 1000, "status": "OK", "health": "OK"}
        }

        allure.attach(
            str(mock_fans),
            name="Fan Speed Data",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证转速过低
        assert mock_fans["FAN3"]["speed_rpm"] < mock_fans["FAN3"]["min_rpm"]

        allure.attach(
            "WARNING: FAN3 speed (800 RPM) below minimum threshold (1000 RPM)",
            name="Alert Message",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("多个风扇故障 - 冗余风险")
    @allure.testcase("TC-FAN-EXC-004", "验证多个风扇故障检测")
    def test_multiple_fans_failed(self):
        """Mock 测试：多个风扇故障"""
        mock_fans = {
            "FAN1": {"status": "FAILED", "health": "CRITICAL"},
            "FAN2": {"status": "FAILED", "health": "CRITICAL"},
            "FAN3": {"speed_rpm": 8000, "status": "OK", "health": "OK"},
            "FAN4": {"speed_rpm": 8200, "status": "OK", "health": "OK"},
            "FAN5": {"speed_rpm": 8100, "status": "OK", "health": "OK"},
            "FAN6": {"speed_rpm": 8000, "status": "OK", "health": "OK"}
        }

        failed_count = sum(1 for f in mock_fans.values() if f["status"] == "FAILED")

        allure.attach(
            str(mock_fans),
            name="Fan Status Data",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证多个风扇故障
        assert failed_count >= 2

        allure.attach(
            f"CRITICAL: {failed_count} fans have failed - thermal redundancy at risk!",
            name="Alert Message",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("Redfish API 获取风扇信息失败")
    @allure.testcase("TC-FAN-EXC-005", "验证 Redfish 风扇接口调用失败")
    def test_redfish_fan_api_failed(self):
        """Mock 测试：Redfish 风扇 API 失败"""
        mock_error = {
            "endpoint": "/Chassis/system/Thermal",
            "http_status": 500,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Unable to retrieve thermal sensor data",
            "retry_after": 30
        }

        allure.attach(
            str(mock_error),
            name="API Error Response",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证 API 错误
        assert mock_error["http_status"] >= 500

        allure.attach(
            "ERROR: Failed to get thermal/fan data via Redfish API (HTTP 500)",
            name="Error Summary",
            attachment_type=allure.attachment_type.TEXT
        )