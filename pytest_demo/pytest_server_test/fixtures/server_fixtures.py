"""
服务器连接 Fixtures
"""
import pytest
import yaml


@pytest.fixture(scope="session")
def server_config():
    """加载服务器配置"""
    with open("config/servers.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def expected_values():
    """加载预期值配置"""
    with open("config/expected_values.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def server_data(server_config):
    """获取默认服务器配置"""
    default = server_config.get("default_server", "server_a")
    return server_config["servers"].get(default, {})


@pytest.fixture(scope="session")
def redfish_collector(server_data):
    """Redfish 采集器"""
    from pytest_server_test.core.collectors import RedfishCollector
    config = server_data.get("redfish", {})
    collector = RedfishCollector(config)
    if collector.connect():
        yield collector
        collector.disconnect()
    else:
        pytest.skip("Redfish unavailable")


@pytest.fixture(scope="session")
def ipmi_collector(server_data):
    """IPMI 采集器"""
    from pytest_server_test.core.collectors import IPMICollector
    config = server_data.get("ipmi", {})
    collector = IPMICollector(config)
    if collector.connect():
        yield collector
    else:
        pytest.skip("IPMI unavailable")


@pytest.fixture(scope="session")
def system_collector(server_data):
    """系统命令采集器"""
    from pytest_server_test.core.collectors import SystemCollector
    collector = SystemCollector(server_data)
    if collector.connect():
        yield collector
        collector.disconnect()
    else:
        pytest.skip("SSH unavailable")