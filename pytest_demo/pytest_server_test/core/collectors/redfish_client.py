"""
Redfish API 采集器
"""
import httpx
from .base import BaseCollector, CollectResult


class RedfishCollector(BaseCollector):
    def __init__(self, config: dict):
        self.base_url = config.get("base_url", "").rstrip("/")
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self._session = None

    def connect(self) -> bool:
        try:
            self._session = httpx.Client(timeout=30)
            resp = self._session.get(
                f"{self.base_url}/SessionService/Sessions",
                auth=(self.username, self.password)
            )
            return resp.status_code == 200
        except Exception:
            return False

    def disconnect(self):
        if self._session:
            self._session.close()

    def collect(self, endpoint: str, **kwargs) -> CollectResult:
        try:
            resp = self._session.get(f"{self.base_url}/{endpoint.lstrip('/')}")
            if resp.status_code == 200:
                return CollectResult(True, resp.json(), "redfish", endpoint)
            return CollectResult(False, {}, "redfish", endpoint, f"HTTP {resp.status_code}")
        except Exception as e:
            return CollectResult(False, {}, "redfish", endpoint, str(e))