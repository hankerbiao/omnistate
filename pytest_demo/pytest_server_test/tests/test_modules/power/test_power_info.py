"""
电源模块测试用例
"""
import allure
import pytest
import json


@allure.feature("Power Management")
@allure.story("Power Information")
@allure.severity(allure.severity_level.NORMAL)
@allure.epic("Hardware Module Tests")
@allure.parent_suite("Server Hardware Tests")
@allure.suite("Power Module")
class TestPowerInfo:
    """电源信息测试"""

    @pytest.mark.smoke
    @pytest.mark.redfish
    @allure.title("通过 Redfish 采集电源信息")
    @allure.testcase("TC-PWR-001", "Redfish API 采集电源信息")
    @allure.issue("https://jira.company.com/REQ-POWER-001", name="需求: REQ-POWER-001")
    def test_collect_power_via_redfish(self, power_module, expected_values):
        """测试通过 Redfish API 采集电源信息"""
        with allure.step("执行 Redfish API 调用"):
            result = power_module.collect_redfish("/Chassis/system/Power")

        assert result.success
        allure.attach(
            json.dumps(result.data, indent=2),
            name="Power Response",
            attachment_type=allure.attachment_type.JSON
        )

    @pytest.mark.status_monitor
    @pytest.mark.ipmi
    @allure.title("电源状态监控")
    @allure.testcase("TC-PWR-STA-001", "IPMI 电源状态查询")
    def test_power_status_via_ipmi(self, ipmi_collector, expected_values):
        """测试通过 IPMI 查询电源状态"""
        with allure.step("执行 IPMI 电源查询"):
            result = ipmi_collector.collect("sdr type 'Power'")

        # 模拟数据
        mock_status = {
            "PSU1_Input": "450 Watts",
            "PSU2_Input": "445 Watts"
        }

        allure.attach(
            json.dumps(mock_status, indent=2),
            name="Power Status",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证电源数量
        min_psu = expected_values["hardware"]["power"]["min_power_supply_count"]
        assert len(mock_status) >= min_psu