"""
网卡模块 Mock 测试用例
用于验证 Allure 报告装饰器展示
"""
import allure
import pytest
import json


@allure.feature("Network Management")
@allure.story("Network Interface Information")
@allure.severity(allure.severity_level.NORMAL)
@allure.description("测试网卡接口信息采集功能")
@allure.epic("Hardware Module Tests")
@allure.parent_suite("Server Hardware Tests")
@allure.suite("Network Module")
class TestNetworkInfoMock:
    """网卡信息 Mock 测试"""

    @pytest.mark.smoke
    @allure.title("采集网卡信息 - Redfish API")
    @allure.testcase("TC-NIC-MOCK-001", "验证 Redfish API 返回网卡信息")
    @allure.issue("https://jira.company.com/REQ-NIC-001", name="需求: 网卡信息采集")
    def test_collect_nic_via_redfish_mock(self):
        """Mock 测试：Redfish API 采集网卡信息"""
        mock_response = {
            "Members": [
                {
                    "Id": "NIC1",
                    "Name": "Embedded NIC 1",
                    "Status": {"Health": "OK"},
                    "SpeedMbps": 10000,
                    "MACAddress": "00:1A:2B:3C:4D:5E",
                    "LinkStatus": "Linked"
                },
                {
                    "Id": "NIC2",
                    "Name": "Embedded NIC 2",
                    "Status": {"Health": "OK"},
                    "SpeedMbps": 10000,
                    "MACAddress": "00:1A:2B:3C:4D:5F",
                    "LinkStatus": "Linked"
                },
                {
                    "Id": "NIC3",
                    "Name": "PCIe NIC 1",
                    "Status": {"Health": "OK"},
                    "SpeedMbps": 25000,
                    "MACAddress": "00:1A:2B:3C:4D:60",
                    "LinkStatus": "Linked"
                }
            ]
        }

        allure.attach(
            json.dumps(mock_response, indent=2),
            name="Mock NIC API Response",
            attachment_type=allure.attachment_type.JSON
        )

        assert len(mock_response["Members"]) == 3
        for nic in mock_response["Members"]:
            assert nic["Status"]["Health"] == "OK"
            assert nic["LinkStatus"] == "Linked"

        allure.attach(
            "Found 3 NICs, all status: OK, LinkStatus: Linked",
            name="Validation Result",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Network Management")
@allure.story("Network Link Status")
@allure.severity(allure.severity_level.CRITICAL)
@allure.description("测试网卡链路状态监控功能")
@allure.issue("https://jira.company.com/REQ-NIC-002", name="需求: 网卡链路状态")
class TestNetworkLinkMock:
    """网卡链路状态 Mock 测试"""

    @pytest.mark.status_monitor
    @allure.title("网卡链路状态检测")
    @allure.testcase("TC-NIC-LINK-001", "验证所有网卡链路状态正常")
    def test_network_link_status_mock(self):
        """Mock 测试：网卡链路状态"""
        mock_links = {
            "NIC1": {"link_status": "up", "speed_gbps": 10, "duplex": "full"},
            "NIC2": {"link_status": "up", "speed_gbps": 10, "duplex": "full"},
            "NIC3": {"link_status": "up", "speed_gbps": 25, "duplex": "full"}
        }

        allure.attach(
            json.dumps(mock_links, indent=2),
            name="Mock Link Status Data",
            attachment_type=allure.attachment_type.JSON
        )

        for nic, status in mock_links.items():
            assert status["link_status"] == "up"
            assert status["duplex"] == "full"

        allure.attach(
            "All network links are up and running at full duplex",
            name="Validation Result",
            attachment_type=allure.attachment_type.TEXT
        )