"""
存储模块 Mock 测试用例
用于验证 Allure 报告装饰器展示
"""
import allure
import pytest
import json


@allure.feature("Storage Management")
@allure.story("Storage Information")
@allure.severity(allure.severity_level.NORMAL)
@allure.description("测试存储信息采集功能")
@allure.epic("Hardware Module Tests")
@allure.parent_suite("Server Hardware Tests")
@allure.suite("Storage Module")
class TestStorageInfoMock:
    """存储信息 Mock 测试"""

    @pytest.mark.smoke
    @allure.title("采集存储信息 - Redfish API")
    @allure.testcase("TC-STR-MOCK-001", "验证 Redfish API 返回存储信息")
    @allure.issue("https://jira.company.com/REQ-STR-001", name="需求: 存储信息采集")
    def test_collect_storage_via_redfish_mock(self):
        """Mock 测试：Redfish API 采集存储信息"""
        mock_response = {
            "Members": [
                {
                    "Id": "RAID1",
                    "Name": "Embedded RAID Controller",
                    "Status": {"Health": "OK"},
                    "Drives": [
                        {"Id": "DRV1", "CapacityBytes": 1920383410176, "MediaType": "SSD"},
                        {"Id": "DRV2", "CapacityBytes": 1920383410176, "MediaType": "SSD"},
                        {"Id": "DRV3", "CapacityBytes": 7681561500176, "MediaType": "HDD"},
                        {"Id": "DRV4", "CapacityBytes": 7681561500176, "MediaType": "HDD"}
                    ]
                }
            ]
        }

        allure.attach(
            json.dumps(mock_response, indent=2),
            name="Mock Storage API Response",
            attachment_type=allure.attachment_type.JSON
        )

        storage = mock_response["Members"][0]
        assert storage["Status"]["Health"] == "OK"
        assert len(storage["Drives"]) == 4

        total_capacity = sum(d["CapacityBytes"] for d in storage["Drives"])
        allure.attach(
            f"Total storage capacity: {total_capacity / (1024**4):.2f} TB",
            name="Capacity Summary",
            attachment_type=allure.attachment_type.TEXT
        )