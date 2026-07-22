"""依赖注入组合根（Composition Root）。

把 ``app.py`` 里散落的服务构造与逐参数传递收敛到单一对象。新增一个横切关注点
（追踪、指标、缓存、自定义负载均衡等）时，只需在此注册并挂到容器，路由与管线
通过 ``container.xxx`` 取用，无需改动任何函数签名。

这是项目「可扩展性」的核心支点：所有可替换组件都通过协议（``Repository`` /
``LoadBalancer``）声明依赖，具体实现在此装配。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import GatewaySettings
from ..core.load_balancer import LoadBalancer, RoundRobinLoadBalancer
from ..core.matching import CapabilityMatcher
from ..core.pipeline import GatewayPipeline
from ..infrastructure.repository import Repository
from ..infrastructure.sqlite_repository import SQLiteRepository
from ..core.security import GatewayAuth
from ..infrastructure.upstream import UpstreamClient


@dataclass
class GatewayContainer:
    """网关运行所需的全部服务实例。"""

    settings: GatewaySettings
    repository: Repository
    auth: GatewayAuth
    load_balancer: LoadBalancer
    matcher: CapabilityMatcher
    upstream_client: UpstreamClient
    pipeline: GatewayPipeline

    @classmethod
    def build(cls, settings: GatewaySettings | None = None) -> "GatewayContainer":
        """按当前配置装配所有服务。

        替换存储 / 负载均衡 / 限流策略时，改这里即可，调用方无感。
        """
        settings = settings or GatewaySettings.from_env()

        repository: Repository = SQLiteRepository(db_path=settings.db_path)
        auth = GatewayAuth(repository)
        load_balancer: LoadBalancer = RoundRobinLoadBalancer(
            settings.upstream_base_urls
        )
        matcher = CapabilityMatcher()
        upstream_client = UpstreamClient(settings)
        pipeline = GatewayPipeline(
            auth=auth,
            matcher=matcher,
            load_balancer=load_balancer,
            upstream_client=upstream_client,
            repository=repository,
            settings=settings,
        )

        return cls(
            settings=settings,
            repository=repository,
            auth=auth,
            load_balancer=load_balancer,
            matcher=matcher,
            upstream_client=upstream_client,
            pipeline=pipeline,
        )
