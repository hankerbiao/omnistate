# Attachments HTTP API

基础路径：`/api/v1/attachments`（由 `app/shared/api/main.py` 挂载）。

统一响应格式：`{"code": 0, "message": "ok", "data": ...}`。  
详见 [API 约定](../../reference/api-conventions.md)。

## 鉴权

所有接口依赖 `get_current_user`，需携带有效 JWT Bearer Token。  
**当前无独立 RBAC 权限码**（任意登录用户均可上传、列表、删除）。

上传人从 token 解析 `user_id`；解析失败时使用 `anonymous`。

## 接口一览

| 方法 | 路径 | 状态码 | 说明 |
|------|------|--------|------|
| `POST` | `/upload` | 201 | 上传文件（multipart/form-data） |
| `GET` | `/{file_id}` | 200 | 附件详情（含预签名下载链接） |
| `GET` | `/{file_id}/download` | 200 | 仅返回预签名下载 URL |
| `DELETE` | `/{file_id}` | 200 | 逻辑删除 |
| `GET` | `` | 200 | 附件列表（分页 + 按上传人筛选） |

## POST /upload

**Content-Type**：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | 文件 | 是 | 二进制内容 |

**限制**：单文件最大 **100MB**，超限返回 HTTP 413。

### 成功响应（`UploadResponse`）

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "file_id": "550e8400-e29b-41d4-a716-446655440000",
    "original_filename": "report.pdf",
    "storage_path": "attachments/attachments/550e8400-e29b-41d4-a716-446655440000.pdf",
    "size": 204800,
    "content_type": "application/pdf",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "uploaded_at": "2026-06-04T10:00:00Z"
  }
}
```

前端拿到 `file_id` 后，在业务表单（如测试用例）的 `attachments` 数组中引用即可。

### curl 示例

```bash
curl -X POST "http://localhost:8000/api/v1/attachments/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/report.pdf"
```

## GET /{file_id}

返回 `AttachmentInfo`，在 upload 字段基础上增加：

| 字段 | 说明 |
|------|------|
| `uploaded_by` | 上传人 user_id |
| `download_url` | 预签名下载链接（默认 7 天有效） |

附件不存在时返回 **404**。

## GET /{file_id}/download

Query 参数：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `expires_seconds` | `int` | 配置值（604800） | 链接有效期（秒） |

响应（`DownloadResponse`）：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "download_url": "http://localhost:9000/attachments/attachments/550e8400...?X-Amz-...",
    "expires_in": 604800
  }
}
```

适合列表页不预生成 URL、用户点击下载时再请求的场景。

## DELETE /{file_id}

逻辑删除，响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "file_id": "550e8400-e29b-41d4-a716-446655440000",
    "deleted": true
  }
}
```

已删除的 `file_id` 再次被业务引用时会校验失败。MinIO 中的对象**不会**立即删除。

## GET /（列表）

Query 参数：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `uploaded_by` | `str` | — | 按上传人筛选 |
| `limit` | `int` | 100 | 返回条数上限 |
| `skip` | `int` | 0 | 跳过条数 |

响应（`AttachmentListResponse`）：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "file_id": "...",
        "original_filename": "report.pdf",
        "storage_path": "attachments/attachments/....pdf",
        "size": 204800,
        "content_type": "application/pdf",
        "uploaded_by": "user-001",
        "uploaded_at": "2026-06-04T10:00:00Z",
        "download_url": null
      }
    ],
    "total": 1
  }
}
```

列表项**刻意不返回** `download_url`，避免批量生成预签名 URL；需要时调 `GET /{file_id}` 或 `GET /{file_id}/download`。

## 错误码

| HTTP | 场景 |
|------|------|
| 401 | 未登录或 token 无效 |
| 404 | `file_id` 不存在或已逻辑删除 |
| 413 | 文件超过 100MB |
| 500 | MinIO 上传失败、Mongo 写入失败等（上传失败会尝试回滚 MinIO 对象） |

## Pydantic 模型位置

`app/modules/attachments/schemas/attachment.py`：

- `UploadResponse`
- `AttachmentInfo`
- `AttachmentListResponse`
- `DeleteResponse`
- `DownloadResponse`
- `DispatchResponse`（预留，当前 API 未直接使用）
