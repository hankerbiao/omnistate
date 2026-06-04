# Attachments 数据模型

附件模块只有一个 MongoDB 文档模型；业务模块（如测试用例）以**嵌套 JSON 数组**形式引用附件，不另建关联表。

## AttachmentDoc

定义：`app/modules/attachments/repository/models/attachment.py`  
集合名：`attachments`

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file_id` | `str` | 是 | 业务主键，UUID，上传时生成 |
| `original_filename` | `str` | 是 | 用户上传时的原始文件名 |
| `bucket` | `str` | 是 | MinIO bucket，通常与配置 `minio.bucket` 一致 |
| `object_name` | `str` | 是 | MinIO 对象路径，格式 `attachments/{file_id}.{ext}` |
| `size` | `int` | 是 | 文件大小（字节） |
| `content_type` | `str` | 是 | MIME 类型，未知时为 `application/octet-stream` |
| `sha256` | `str` | 否 | 上传时计算的 SHA256 十六进制摘要 |
| `uploaded_by` | `str` | 是 | 上传人 user_id；匿名上传时为 `anonymous` |
| `uploaded_at` | `datetime` | 是 | 上传时间（UTC） |
| `is_deleted` | `bool` | 是 | 逻辑删除标记，默认 `false` |
| `deleted_at` | `datetime` | 否 | 逻辑删除时间 |
| `created_at` | `datetime` | 是 | 文档创建时间（Beanie 自动维护） |
| `updated_at` | `datetime` | 是 | 文档更新时间（`@before_event` 钩子） |

### 索引

- `file_id`：按业务 ID 查询（enrich、详情、下载）
- `uploaded_by`：列表筛选

Beanie 开启 `use_revision = True`，支持乐观锁修订。

### MinIO 对象命名

上传时 Service 生成 `object_name`：

```
attachments/{file_id}.{extension}   # 有扩展名
attachments/{file_id}               # 无扩展名
```

`storage_path`（API 与 enrich 输出）为 `{bucket}/{object_name}` 的组合字符串，**不是**单独持久化字段。

## 业务侧附件结构

业务文档（如 `TestCaseDoc.attachments`）存储 enrich 后的快照，典型字段：

```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "firmware.bin",
  "storage_path": "attachments/attachments/550e8400-e29b-41d4-a716-446655440000.bin",
  "size": 1048576,
  "content_type": "application/octet-stream",
  "uploaded_at": "2026-04-30T08:00:00+00:00"
}
```

前端提交时**最少只需** `file_id`；后端在写入前补齐其余字段。前端可额外携带 `description` 等业务字段，enrich 时会保留（除 `file_id` 外 merge 进结果）。

### 与 TestCaseDoc 的关系

- `TestCaseDoc.attachments`：`List[Dict[str, Any]]`，默认 `[]`
- 仅在**创建**测试用例时走 `_validate_and_enrich_attachments`（更新路径是否 enrich 以实现为准，改动前读 `TestCaseService`）
- `TestRequirementDoc` 也有 `attachments` 字段，但当前 **requirement 创建未调用** attachments 校验 enrich

## Execution 侧 file 参数结构

执行任务 `parameters` 中，文件类型参数约定：

```json
{
  "firmware": {
    "type": "file",
    "file_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

任务创建时 `enrich_single` 会补充：

| 字段 | 说明 |
|------|------|
| `original_filename` | 来自 AttachmentDoc |
| `storage_path` | `bucket/object_name` |
| `bucket` / `object_name` | MinIO 定位 |
| `size` / `content_type` / `sha256` | 元数据 |
| `uploaded_at` | ISO 8601 字符串 |
| `download_url` |  fresh 预签名 URL |

下发 payload 构造（`build_dispatch_task_data`）进一步将 file 参数提取到顶层 `files`：

```json
{
  "cases": [{
    "parameters": { "firmware": "" }
  }],
  "files": {
    "firmware": {
      "url": "http://minio:9000/attachments/...?X-Amz-...",
      "sha256": "abc123..."
    }
  }
}
```

此时依赖 parameters 中已 enrich 的 `object_name` 和 `sha256`；若 MinIO 不可用，会保留原 `download_url` 或跳过提取（见 execution 单测 `test_refresh_file_param_urls_graceful_minio_failure`）。

## Service 层 enrich 方法对比

| 方法 | 用途 | 批量 | 含 download_url |
|------|------|------|-----------------|
| `enrich_for_dispatch(file_ids)` | 批量校验 + 元数据 | 是（单次 `$in` 查询） | 否 |
| `enrich_single(file_id)` | 单文件 + 下发 | 否 | 是 |
| `get_attachment_info(file_id)` | API 详情 | 否 | 是 |

缺失或已删除附件时，`enrich_*` 方法抛出 `KeyError`，消息形如 `attachment not found or deleted: {file_id}`。
