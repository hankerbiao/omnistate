# 附件管理模块（attachments）

管理测试需求和测试用例的附件上传、存储和查询。

## 目录结构

- `api/` — HTTP 路由
- `schemas/` — API 请求/响应模型
- `service/` — 附件处理服务
- `repository/models/` — Beanie 文档模型

## 核心模型

- `AttachmentDoc` — 附件文档

## API 前缀

- `/api/v1/attachments`

## 文件存储

后端存储通过 MinIO 完成，配置见 `app/shared/minio/`。
