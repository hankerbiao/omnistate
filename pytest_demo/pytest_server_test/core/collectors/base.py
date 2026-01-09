"""
数据采集器基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class CollectResult:
    """采集结果"""
    success: bool
    data: Dict[str, Any]
    source: str  # redfish/ipmi/system
    endpoint: str
    error: str = None


class BaseCollector(ABC):
    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def disconnect(self): ...

    @abstractmethod
    def collect(self, endpoint: str, **kwargs) -> CollectResult: ...