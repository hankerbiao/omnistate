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

### 允许的依赖方向

```
API → Application → Domain
API → Application → Repository/Models（通过端口/应用服务）
Application → Repository/Models（必要时直接使用）
Domain → （不依赖 API、Service、Infrastructure）
跨模块写操作 → 通过 Application 端口协议
```

## 模块关系

- `workflow`
  业务流转基础设施
- `test_specs`
  需求与用例定义层，读写 workflow 状态投影
- `execution`
  执行任务编排层，读取 test_specs 的用例与自动化配置（详见 [Execution 模块文档](/modules/execution/)）
- `execution_plan`
  手工执行计划与结果回填
- `auth`
  资源级 RBAC 服务
- `attachments`
  附件引用能力
- `terminal`
  远程终端能力
- `ai_analysis`
  AI 驱动的测试资产分析（质量、冗余、覆盖度）
- `failure_analysis`
  执行失败智能分析与模式分类
- `lineage`
  需求-用例-执行的血缘追溯
- `search`
  跨模块统一全文搜索
- `system_config`
  全局配置管理与 AI 连接测试
- `test_case_collection`
  预制用例集管理
- `shared`
  横切基础设施和公共能力

## 启动链路

服务启动时依次执行：

1. 连接 MongoDB
2. 初始化 Beanie 文档模型（各模块通过 `DOCUMENT_MODELS` 导出在 `repository/models/__init__.py` 中，`app/shared/infrastructure/bootstrap.py` 统一聚合）
3. 校验 workflow 配置一致性
4. 初始化应用级基础设施（RabbitMQ、Kafka、执行调度器）
5. 初始化系统默认配置
6. 注册异常处理器与 API 路由

对应入口见 `app/main.py`。

## 哪些地方最值得先读

- 要理解 HTTP 接入：先读 `app/shared/api/main.py`
- 要理解业务模块边界：先读 `app/modules/*/api` 和 `app/modules/*/application`
- 要理解数据库形态：读 `app/modules/*/repository/models`
- 要理解共性基础设施：读 `app/shared/*`
- 要理解模块内分层约定：读各模块的 `README.md`
