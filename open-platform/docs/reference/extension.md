# 扩展指南

## 新增开放能力

在 `backend/gateway_service/core/catalog.py` 的 `CAPABILITIES` 中增加一条 `Capability`。

```python
Capability(
    id="cap_new_feature",
    name="新能力",
    category="集成",
    method="POST",
    path="/api/v1/open/new-feature",
    summary="一句话摘要",
    description="详细说明。",
    scope="new_feature:write",
    handler="proxy",
    upstreamPath="/api/v1/new-feature",
    params=[
        {
            "name": "project_id",
            "type": "string",
            "required": True,
            "description": "项目 ID。",
        }
    ],
    sampleResponse='{"code": 0, "data": {}}',
)
```

新增后会自动影响：

- 开放 API 路由匹配
- 控制台能力目录
- 调试探针能力选择
- 用户权限配置

## 新增代理阶段

在 `core/pipeline.py` 中新增私有阶段方法，并插入 `handle()`：

```python
async def handle(self, request: Request) -> Response:
    ctx = ProxyContext(...)
    self._match(ctx)
    self._authenticate(ctx)
    self._rewrite_request(ctx)
    self._choose_upstream(ctx)
    ...
```

适合新增：

- 请求体改写
- 参数兼容
- 响应缓存
- 链路追踪
- 灰度路由

## 替换仓储

当前默认仓储是 SQLite。要替换为 Redis、PostgreSQL 或远程服务：

1. 实现 `infrastructure/repository.py` 中的仓储协议。
2. 在 `common/container.py` 中替换具体实现。
3. 补充迁移或初始化逻辑。
4. 增加仓储层单元测试。

## 替换负载均衡

当前策略是轮询。要替换为权重、健康探测或一致性哈希：

1. 实现 `core/load_balancer.py` 中的同形接口。
2. 在 `GatewayContainer.build()` 中替换。
3. 增加并发和故障场景测试。

## 前端新增页面

1. 在 `frontend/src/pages/` 新增页面组件。
2. 在布局或导航配置中注册入口。
3. 在 `frontend/src/types.ts` 增加类型。
4. 在 `frontend/src/services/api.ts` 增加客户端方法。
5. 在 `frontend/src/mock/handlers.ts` 增加 Mock 分支，便于纯前端演示。
