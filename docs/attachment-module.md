# 附件管理模块

## 概述

附件管理模块提供文件上传、存储、下载和管理功能。文件存储在MinIO对象存储服务中，元数据保存到MongoDB。

## 模块架构

```
backend/app/modules/attachments/
├── api/
│   └── routes.py          # API路由定义
├── schemas/
│   └── attachment.py      # Pydantic模型
├── service/
│   └── attachment_service.py  # 业务逻辑
└── repository/models/
    └── attachment.py      # MongoDB文档模型
```

## 配置项

通过环境变量配置MinIO连接：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO服务地址 |
| `MINIO_ACCESS_KEY` | `minioadmin` | 访问密钥 |
| `MINIO_SECRET_KEY` | `minioadmin` | 秘密密钥 |
| `MINIO_BUCKET` | `attachments` | 存储桶名称 |
| `MINIO_SECURE` | `false` | 是否启用HTTPS |

## 数据模型

### AttachmentDoc (MongoDB文档)

| 字段 | 类型 | 说明 |
|------|------|------|
| `file_id` | string | 文件唯一标识（UUID） |
| `original_filename` | string | 原始文件名 |
| `bucket` | string | MinIO存储桶名称 |
| `object_name` | string | MinIO对象名 |
| `size` | integer | 文件大小（字节） |
| `content_type` | string | MIME类型 |
| `uploaded_by` | string | 上传人ID |
| `uploaded_at` | datetime | 上传时间 |
| `is_deleted` | boolean | 逻辑删除标记 |
| `deleted_at` | datetime | 删除时间 |

## API接口

### 1. 上传附件

```
POST /api/v1/attachments/upload
Content-Type: multipart/form-data

请求参数：
- file: 文件内容

响应：
{
  "file_id": "uuid-string",
  "original_filename": "example.pdf",
  "storage_path": "attachments/uuid.pdf",
  "size": 1024,
  "content_type": "application/pdf",
  "uploaded_at": "2026-03-26T10:00:00"
}
```

### 2. 获取附件信息

```
GET /api/v1/attachments/{file_id}

响应：
{
  "file_id": "uuid-string",
  "original_filename": "example.pdf",
  "storage_path": "attachments/uuid.pdf",
  "size": 1024,
  "content_type": "application/pdf",
  "uploaded_by": "user-id",
  "uploaded_at": "2026-03-26T10:00:00",
  "download_url": "https://..."
}
```

### 3. 获取下载链接

```
GET /api/v1/attachments/{file_id}/download?expires_seconds=3600

响应：
{
  "download_url": "https://minio.example.com/attachments/...",
  "expires_in": 3600
}
```

### 4. 删除附件

```
DELETE /api/v1/attachments/{file_id}

响应：
{
  "file_id": "uuid-string",
  "deleted": true
}
```

### 5. 列出附件

```
GET /api/v1/attachments?uploaded_by=user-id&limit=100&skip=0

响应：
{
  "items": [
    {
      "file_id": "uuid-string",
      "original_filename": "example.pdf",
      "storage_path": "attachments/uuid.pdf",
      "size": 1024,
      "content_type": "application/pdf",
      "uploaded_by": "user-id",
      "uploaded_at": "2026-03-26T10:00:00",
      "download_url": null
    }
  ],
  "total": 1
}
```

### 6. 预留下发接口（暂未实现）

```
POST /api/v1/attachments/{file_id}/dispatch

响应：
{
  "status": 501,
  "detail": "下发给测试框架功能暂未实现"
}
```

## 使用示例

### 前端上传文件

```typescript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('/api/v1/attachments/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const result = await response.json();
// result.storage_path 即为MinIO存储路径
```

### 后端调用

```python
from app.modules.attachments.service import AttachmentService

service = AttachmentService()

# 上传文件
result = await service.upload_file(
    filename="test.pdf",
    content=file_content,
    content_type="application/pdf",
    uploaded_by="user123"
)

# 获取下载链接
download_url = await service.get_download_url(result.file_id)
```

## 限制说明

- 单文件大小限制：100MB
- 逻辑删除：删除操作不会物理删除MinIO中的文件
- 下载链接有效期：默认3600秒（1小时）

## 预留功能

下发给测试框架的接口（`POST /api/v1/attachments/{file_id}/dispatch`）暂未实现，需要后续根据测试框架的具体需求实现：

1. 确定测试框架的接口地址和认证方式
2. 确定文件传输方式（直传、URL分享等）
3. 实现下发状态跟踪和回调机制