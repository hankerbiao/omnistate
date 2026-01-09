"""
系统命令采集器 (SSH)
"""
import paramiko
from .base import BaseCollector, CollectResult


class SystemCollector(BaseCollector):
    def __init__(self, config: dict):
        self.host = config.get("host", "")
        self.port = config.get("port", 22)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self._client = None

    def connect(self) -> bool:
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(
                hostname=self.host, port=self.port,
                username=self.username, password=self.password, timeout=10
            )
            return True
        except Exception:
            return False

    def disconnect(self):
        if self._client:
            self._client.close()

    def collect(self, command: str, **kwargs) -> CollectResult:
        try:
            stdin, stdout, stderr = self._client.exec_command(command, timeout=60)
            output = stdout.read().decode('utf-8')
            if stderr.read():
                return CollectResult(False, {"raw": output}, "system", command, stderr.read().decode())
            return CollectResult(True, {"raw": output}, "system", command)
        except Exception as e:
            return CollectResult(False, {}, "system", command, str(e))