# 架构总览

## 总体形态

DML V4 后端当前是单体 FastAPI 应用，不是微服务。

统一入口：

- `app/main.py`
- `app/shared/api/main.py`

统一 API 响应使用：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## 分层模型

项目目标分层是：

- API 层：路由、依赖注入、请求响应转换
- Application / Service 层：用例编排与业务逻辑
- Repository 层：Beanie 文档与数据访问
- Domain 层：规则、策略、异常

现实上，部分模块已经接近这个目标，部分模块仍有 service 直接访问 Beanie 文档的情况，所以看代码时不要只信目录名，要看真实依赖方向。

## 模块关系

- `workflow`
  业务流转基础设施
- `test_specs`
  需求与用例定义层，读写 workflow 状态投影
- `execution`
  执行任务编排层，读取 test_specs 的用例与自动化配置
- `auth`
  资源级 RBAC 服务
- `attachments`
  附件引用能力
- `terminal`
  远程终端能力
- `shared`
  横切基础设施和公共能力

## 启动链路

服务启动时依次执行：

1. 连接 MongoDB
2. 初始化 Beanie 文档模型
3. 校验 workflow 配置一致性
4. 初始化应用级基础设施
5. 注册异常处理器与 API 路由

对应入口见 `app/main.py`。

## 哪些地方最值得先读

- 要理解 HTTP 接入：先读 `app/shared/api/main.py`
- 要理解业务模块边界：先读 `app/modules/*/api` 和 `app/modules/*/application`
- 要理解数据库形态：读 `app/modules/*/repository/models`
- 要理解共性基础设施：读 `app/shared/*`
