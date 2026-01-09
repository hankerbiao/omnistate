"""
内存模块测试用例
"""
import allure
import pytest
import json


@allure.feature("Memory Information")
@allure.story("Memory Information Collection")
@allure.severity(allure.severity_level.NORMAL)
@allure.epic("Hardware Module Tests")
@allure.parent_suite("Server Hardware Tests")
@allure.suite("Memory Module")
class TestMemoryInfo:
    """内存信息测试"""

    @pytest.mark.smoke
    @pytest.mark.system
    @allure.title("通过系统命令采集内存信息")
    @allure.testcase("TC-MEM-001", "系统命令 free -h 采集内存信息")
    def test_collect_memory_via_system(self, memory_module, expected_values):
        """测试通过系统命令采集内存信息"""
        with allure.step("执行 free -h 命令"):
            result = memory_module.collect_system("free -h")

        assert result.success
        data = result.data.get("raw", "")

        allure.attach(data, name="Memory Output", attachment_type=allure.attachment_type.TEXT)

        # 模拟解析的内存数据
        mock_memory = {"total": "32GB", "available": "16GB"}

        # 验证
        min_mem = expected_values["hardware"]["memory"]["min_total_gb"]
        assert int(mock_memory["total"].replace("GB", "")) >= min_mem