"""
风扇模块 Mock 测试用例
用于验证 Allure 报告装饰器展示
"""
import allure
import pytest
import json


@allure.feature("Fan Management")
@allure.story("Fan Information")
@allure.severity(allure.severity_level.NORMAL)
@allure.description("测试风扇模块信息采集功能")
@allure.epic("Hardware Module Tests")
@allure.parent_suite("Server Hardware Tests")
@allure.suite("Fan Module")
class TestFanInfoMock:
    """风扇信息 Mock 测试"""

    @pytest.mark.smoke
    @allure.title("采集风扇信息 - Redfish API")
    @allure.testcase("TC-FAN-MOCK-001", "验证 Redfish API 返回风扇信息")
    @allure.issue("https://jira.company.com/REQ-FAN-001", name="需求: 风扇信息采集")
    def test_collect_fan_via_redfish_mock(self):
        """Mock 测试：Redfish API 采集风扇信息"""
        mock_response = {
            "Fans": [
                {"Id": "FAN1", "Name": "Fan 1", "SpeedRPM": 5200, "Status": {"Health": "OK"}},
                {"Id": "FAN2", "Name": "Fan 2", "SpeedRPM": 5100, "Status": {"Health": "OK"}},
                {"Id": "FAN3", "Name": "Fan 3", "SpeedRPM": 5300, "Status": {"Health": "OK"}},
                {"Id": "FAN4", "Name": "Fan 4", "SpeedRPM": 5200, "Status": {"Health": "OK"}},
                {"Id": "FAN5", "Name": "Fan 5", "SpeedRPM": 5150, "Status": {"Health": "OK"}},
                {"Id": "FAN6", "Name": "Fan 6", "SpeedRPM": 5250, "Status": {"Health": "OK"}}
            ]
        }

        allure.attach(
            json.dumps(mock_response, indent=2),
            name="Mock Fan API Response",
            attachment_type=allure.attachment_type.JSON
        )

        assert len(mock_response["Fans"]) == 6
        for fan in mock_response["Fans"]:
            assert fan["Status"]["Health"] == "OK"

        allure.attach(
            "Found 6 fans, all status: OK",
            name="Validation Result",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Fan Management")
@allure.story("Fan Speed Control")
@allure.severity(allure.severity_level.NORMAL)
@allure.description("测试风扇转速控制功能")
@allure.issue("https://jira.company.com/REQ-FAN-002", name="需求: 风扇转速控制")
class TestFanSpeedMock:
    """风扇转速 Mock 测试"""

    @pytest.mark.status_monitor
    @allure.title("风扇转速实时监控")
    @allure.testcase("TC-FAN-SPD-001", "验证风扇转速在正常范围内")
    def test_fan_speed_monitoring_mock(self):
        """Mock 测试：风扇转速监控"""
        mock_data = {
            "FAN1": {"speed_rpm": 5200, "min_rpm": 1000, "max_rpm": 10000, "status": "OK"},
            "FAN2": {"speed_rpm": 5100, "min_rpm": 1000, "max_rpm": 10000, "status": "OK"},
            "FAN3": {"speed_rpm": 5300, "min_rpm": 1000, "max_rpm": 10000, "status": "OK"},
            "FAN4": {"speed_rpm": 5200, "min_rpm": 1000, "max_rpm": 10000, "status": "OK"},
            "FAN5": {"speed_rpm": 5150, "min_rpm": 1000, "max_rpm": 10000, "status": "OK"},
            "FAN6": {"speed_rpm": 5250, "min_rpm": 1000, "max_rpm": 10000, "status": "OK"}
        }

        allure.attach(
            json.dumps(mock_data, indent=2),
            name="Mock Fan Speed Data",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证转速范围
        for fan, data in mock_data.items():
            assert data["min_rpm"] <= data["speed_rpm"] <= data["max_rpm"]
            assert data["status"] == "OK"

        allure.attach(
            "All fan speeds are within normal range",
            name="Validation Result",
            attachment_type=allure.attachment_type.TEXT
        )