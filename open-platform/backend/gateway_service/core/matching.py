"""开放能力路由匹配。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .catalog import CAPABILITIES
from ..domain.models import Capability


@dataclass(frozen=True, slots=True)
class RouteMatch:
    capability: Capability
    path_params: dict[str, str]


class CapabilityMatcher:
    """将请求 method/path 映射到开放能力。"""

    def __init__(self) -> None:
        self._compiled: list[tuple[str, re.Pattern[str], Capability]] = []
        for capability in CAPABILITIES:
            pattern = "^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", capability.path) + "$"
            self._compiled.append((capability.method.value, re.compile(pattern), capability))

    def match(self, method: str, path: str) -> RouteMatch | None:
        method = method.upper()
        for expected_method, pattern, capability in self._compiled:
            if expected_method != method:
                continue
            match = pattern.match(path)
            if match:
                return RouteMatch(capability=capability, path_params=match.groupdict())
        return None


def resolve_upstream_path(capability: Capability, path_params: dict[str, str]) -> str:
    """Resolve the explicit DML route for a proxied capability."""
    if not capability.upstreamPath:
        raise ValueError(f"proxy capability {capability.id} must define upstreamPath")

    upstream_path = capability.upstreamPath
    for name, value in path_params.items():
        upstream_path = upstream_path.replace("{" + name + "}", value)
    return upstream_path
