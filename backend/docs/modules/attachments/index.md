# Attachments 模块

## 模块职责

`attachments` 负责附件元数据管理，为业务表单和测试用例等实体提供文件引用能力。

## 核心目录

- `api/routes.py`
- `service/attachment_service.py`
- `repository/models/attachment.py`
- `schemas/attachment.py`

## 典型使用场景

- 前端先上传文件
- 业务表单只持有附件标识
- 后端在业务写入时校验并补齐附件信息

## 与其他模块的关系

- `test_specs` 的 test case 创建会校验附件并补全存储路径等信息
- MinIO 配置位于 `app/shared/minio/*`

## 关键字段与配置说明

### 附件字段

- `file_id`
  附件业务 ID，也是业务表单里最常引用的字段
- `bucket`
  对象存储桶名称
- `object_name`
  对象存储中的文件对象名
- `original_filename`
  原始文件名
- `content_type`
  文件 MIME 类型
- `size`
  文件大小

### 关联后的业务字段

当业务模块引用附件时，通常不会只保存裸 `file_id`，还会补齐：

- `storage_path`
  组合自 `bucket/object_name`
- `uploaded_at`
  上传时间

### 配置项

- MinIO 相关配置在 `app/shared/minio/config.py`
- 业务层通常不直接关心上传实现，但会依赖这些配置是否正确以保证附件元数据可解析

## 风险点

- 附件元数据与实际存储对象不一致时，业务写入会失败
