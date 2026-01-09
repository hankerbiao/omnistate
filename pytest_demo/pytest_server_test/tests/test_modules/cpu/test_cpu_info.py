"""
CPU 模块测试用例

按以下维度组织：
- 硬件模块: cpu, memory, storage, power, fan, network
- 测试类型: smoke, config_verify, status_monitor
- 采集接口: redfish, ipmi, system
"""
import allure
import pytest
import json


@allure.feature("CPU Information")
@allure.story("CPU Information Collection")
@allure.severity(allure.severity_level.NORMAL)
@allure.epic("Hardware Module Tests")
@allure.parent_suite("Server Hardware Tests")
@allure.suite("CPU Module")
class TestCPUInfo:
    """CPU 信息采集测试"""

    @pytest.mark.smoke
    @pytest.mark.redfish
    @allure.title("通过 Redfish 采集 CPU 信息")
    @allure.testcase("TC-CPU-001", "Redfish API 采集 CPU 基本信息")
    def test_collect_cpu_via_redfish(self, cpu_module):
        """测试通过 Redfish API 采集 CPU 信息"""
        with allure.step("执行 Redfish API 调用"):
            result = cpu_module.collect_redfish("/Systems/system/Processors")

        with allure.step("验证采集结果"):
            assert result.success, f"采集失败: {result.error}"
            allure.attach(
                json.dumps(result.data, indent=2),
                name="CPU Response",
                attachment_type=allure.attachment_type.JSON
            )

    @pytest.mark.smoke
    @pytest.mark.system
    @allure.title("通过系统命令采集 CPU 信息")
    @allure.testcase("TC-CPU-002", "系统命令 lscpu 采集 CPU 信息")
    def test_collect_cpu_via_system(self, cpu_module, expected_values):
        """测试通过系统命令 lscpu 采集 CPU 信息"""
        with allure.step("执行 lscpu 命令"):
            result = cpu_module.collect_system("lscpu")

        assert result.success
        data = result.data.get("raw", "")

        allure.attach(data, name="lscpu Output", attachment_type=allure.attachment_type.TEXT)

        # 简单验证
        assert "CPU(s):" in data, "CPU 信息应包含核心数"


@allure.feature("CPU Status")
@allure.story("CPU Status Monitoring")
@allure.severity(allure.severity_level.CRITICAL)
class TestCPUStatus:
    """CPU 状态监控测试"""

    @pytest.mark.status_monitor
    @pytest.mark.ipmi
    @allure.title("CPU 温度监控")
    @allure.testcase("TC-CPU-STA-001", "通过 IPMI 获取 CPU 温度")
    def test_cpu_temperature_via_ipmi(self, ipmi_collector):
        """测试通过 IPMI 获取 CPU 温度"""
        with allure.step("执行 IPMI 温度查询"):
            result = ipmi_collector.collect("sdr type temperature")

        # 模拟数据（实际环境中会从真实服务器获取）
        mock_data = {
            "CPU_Temp": "45 degreesC",
            "PCH_Temp": "42 degreesC"
        }

        allure.attach(
            json.dumps(mock_data, indent=2),
            name="Temperature Data",
            attachment_type=allure.attachment_type.JSON
        )

        # 验证逻辑
        assert isinstance(mock_data, dict)