"""
硬件模块 Fixtures
"""
import pytest
from pytest_server_test.core.collectors import CollectResult


class HardwareModule:
    """硬件模块封装"""

    def __init__(self, name, collectors):
        self.name = name
        self.collectors = collectors

    def collect(self, source: str, endpoint: str, **kwargs) -> CollectResult:
        """统一采集接口"""
        collector = self.collectors.get(source)
        if collector:
            return collector.collect(endpoint, **kwargs)
        return CollectResult(False, {}, source, endpoint, f"{source} collector not available")

    def collect_redfish(self, endpoint: str) -> CollectResult:
        return self.collect("redfish", endpoint)

    def collect_ipmi(self, command: str) -> CollectResult:
        return self.collect("ipmi", command)

    def collect_system(self, command: str) -> CollectResult:
        return self.collect("system", command)


@pytest.fixture
def cpu_module(redfish_collector, ipmi_collector, system_collector):
    collectors = {"redfish": redfish_collector, "ipmi": ipmi_collector, "system": system_collector}
    yield HardwareModule("CPU", collectors)


@pytest.fixture
def memory_module(redfish_collector, ipmi_collector, system_collector):
    collectors = {"redfish": redfish_collector, "ipmi": ipmi_collector, "system": system_collector}
    yield HardwareModule("Memory", collectors)


@pytest.fixture
def storage_module(redfish_collector, ipmi_collector, system_collector):
    collectors = {"redfish": redfish_collector, "ipmi": ipmi_collector, "system": system_collector}
    yield HardwareModule("Storage", collectors)


@pytest.fixture
def power_module(redfish_collector, ipmi_collector, system_collector):
    collectors = {"redfish": redfish_collector, "ipmi": ipmi_collector, "system": system_collector}
    yield HardwareModule("Power", collectors)


@pytest.fixture
def fan_module(redfish_collector, ipmi_collector, system_collector):
    collectors = {"redfish": redfish_collector, "ipmi": ipmi_collector, "system": system_collector}
    yield HardwareModule("Fan", collectors)