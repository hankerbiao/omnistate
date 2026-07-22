"""负载均衡。"""

from __future__ import annotations

import itertools
from typing import Protocol, runtime_checkable


@runtime_checkable
class LoadBalancer(Protocol):
    """上游选择契约。

    默认实现 :class:`RoundRobinLoadBalancer` 轮询选择上游；接入一致性哈希、权重或
    服务发现时提供另一个满足该协议的对象即可，调用方无需改动。
    """

    def choose(self) -> str | None: ...


class RoundRobinLoadBalancer:
    """轮询负载均衡器。"""

    def __init__(self, upstreams: tuple[str, ...]) -> None:
        self._upstreams = upstreams
        self._counter = itertools.count()

    def choose(self) -> str | None:
        if not self._upstreams:
            return None
        idx = next(self._counter) % len(self._upstreams)
        return self._upstreams[idx]
