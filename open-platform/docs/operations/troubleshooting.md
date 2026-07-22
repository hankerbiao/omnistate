# 故障排查

## 网关启动失败

检查端口是否被占用：

```bash
lsof -i :8820
```

检查配置是否非法：

- `DML_GATEWAY_PORT` 必须在 1-65535。
- `DML_GATEWAY_UPSTREAMS` 至少包含一个地址。
- 超时配置必须大于 0。
- `DML_GATEWAY_UPSTREAM_AUTH_SECRET` 不能为空。

## 前端无法访问网关

确认：

- 网关健康检查通过。
- 前端环境变量 `VITE_OPEN_PLATFORM_API_BASE_URL` 指向正确地址。
- 浏览器控制台没有 CORS 错误。
- `DML_GATEWAY_CORS_ORIGINS` 包含前端来源。

## 开放 API 401

常见原因：

- 未携带 `Authorization: Bearer <API Key>`。
- API Key 不存在。
- API Key 已撤销。
- 使用了控制台 Token 调开放 API。

## 开放 API 403

常见原因：

- API Key 缺少目标能力 Scope。
- 密钥所属用户没有该能力授权。
- 当前用户被配额或权限策略限制。

## 开放 API 404

表示没有匹配到 `Capability`。检查：

- HTTP 方法是否一致。
- 路径是否包含 `/api/v1/open`。
- 路径参数位置是否正确。
- 新能力是否已加入 `core/catalog.py`。

## 开放 API 429

表示超出配额、RPM 或并发限制。可在用户配额页面调整。

## 开放 API 503

通常与上游有关：

- DML 主后端未启动。
- `DML_GATEWAY_UPSTREAMS` 配置错误。
- 上游连续失败触发熔断。
- 网关到上游网络不通。

## 文档站构建失败

先确认依赖已安装：

```bash
cd docs
npm install
npm run build
```

如果提示 Markdown 或 Mermaid 解析错误，优先检查最近编辑的代码块围栏是否闭合。
