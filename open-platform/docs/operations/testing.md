# 测试与质量

## 后端测试

```bash
cd backend
uv run pytest tests -v
```

单测重点：

- 控制台鉴权
- 上游认证
- 能力执行
- 请求管线错误分支
- 仓储读写行为

## 后端代码检查

当前 `backend/pyproject.toml` 配置了 Ruff：

```bash
cd backend
uv run ruff check gateway_service tests
```

## 前端测试

```bash
cd frontend
npm run test:run
```

## 前端构建

```bash
cd frontend
npm run build
```

## 文档构建

```bash
cd docs
npm run build
```

## 变更检查清单

提交前建议确认：

- 新增开放能力已补 `Capability`、Scope、参数和示例响应。
- 控制台能展示新增能力。
- API 调试台可以选择并探测新增能力。
- 权限和配额边界有测试。
- 错误响应仍符合统一 envelope。
- 前端类型与后端响应字段一致。
- 文档中的命令、端口和环境变量与代码一致。
