"""
IPMI 采集器
"""
import subprocess
from .base import BaseCollector, CollectResult


class IPMICollector(BaseCollector):
    def __init__(self, config: dict):
        self.host = config.get("host", "")
        self.user = config.get("user", "")
        self.password = config.get("password", "")

    def connect(self) -> bool:
        try:
            result = subprocess.run(
                ["ipmitool", "-H", self.host, "-U", self.user, "-P", self.password, "sdr", "list"],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def disconnect(self):
        pass

    def collect(self, command: str, **kwargs) -> CollectResult:
        try:
            cmd = ["ipmitool", "-H", self.host, "-U", self.user, "-P", self.password] + command.split()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return CollectResult(True, {"raw": result.stdout}, "ipmi", command)
            return CollectResult(False, {}, "ipmi", command, result.stderr)
        except Exception as e:
            return CollectResult(False, {}, "ipmi", command, str(e))