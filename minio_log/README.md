# MinIO 日志管理 SDK

用于将测试日志文件按照指定路径规则上传到 MinIO 对象存储的 Python SDK。

## 功能特性

- ✅ 普通文件上传（适合小文件）
- ✅ 大文件分块上传（适合大文件）
- ✅ 智能上传（自动选择上传方式）
- ✅ 批量上传多个文件
- ✅ 文件列表查询
- ✅ 文件删除
- ✅ 生成预签名下载链接

## 安装依赖

```bash
pip install minio
```

## 快速开始

### 基本使用

```python
from minio_log_manager import MinioLogManager

# 初始化（使用默认配置）
mgr = MinioLogManager()

# 上传日志文件
url = mgr.upload_test_log(
    project="PCIe-Switch-FW",
    machine_ip="10.17.154.252",
    test_plan_id="TP-20260312-001",
    local_file_path="./test_result.log"
)

if url:
    print(f"上传成功！下载链接: {url}")
```

### 自定义配置

```python
mgr = MinioLogManager(
    endpoint="10.17.154.252:9003",
    access_key="admin",
    secret_key="12345678",
    bucket_name="auto-test-logs",
    secure=False
)
```

## 大文件上传

### 方法1: 智能上传（推荐）

自动根据文件大小选择上传方式：

```python
url = mgr.upload_log_auto(
    project="PCIe-Switch-FW",
    machine_ip="10.17.154.252",
    test_plan_id="TP-20260312-001",
    local_file_path="./large_log.log"
)
```

**参数说明：**
- `large_file_threshold`: 大文件阈值，默认 100MB
- `chunk_size`: 分块大小，默认 5MB

**工作原理：**
- 文件 < 100MB：使用普通上传（`fput_object`）
- 文件 >= 100MB：使用分块上传（`put_object` + 流式传输）

### 方法2: 显式使用分块上传

```python
url = mgr.upload_large_file(
    project="PCIe-Switch-FW",
    machine_ip="10.17.154.252",
    test_plan_id="TP-20260312-001",
    local_file_path="./huge_log.log",
    chunk_size=10 * 1024 * 1024  # 10MB 分块
)
```

**适用场景：**
- 文件大小超过 100MB
- 需要自定义分块大小
- 需要更好的网络容错能力

## 批量上传

```python
files = [
    "./log1.log",
    "./log2.log",
    "./log3.log"
]

results = mgr.upload_multiple_logs(
    project="PCIe-Switch-FW",
    machine_ip="10.17.154.252",
    test_plan_id="TP-20260312-BATCH",
    local_file_paths=files
)

for file_path, result in results.items():
    print(f"{file_path}: {result}")
```

## 文件管理

### 列出文件

```python
# 列出所有文件
files = mgr.list_log_files()

# 按项目过滤
files = mgr.list_log_files(project="PCIe-Switch-FW")

# 按日期过滤
files = mgr.list_log_files(
    project="PCIe-Switch-FW",
    date_str="2026-03-12"
)

# 按测试计划过滤
files = mgr.list_log_files(
    project="PCIe-Switch-FW",
    machine_ip="10.17.154.252",
    date_str="2026-03-12",
    test_plan_id="TP-20260312-001"
)
```

### 删除文件

```python
success = mgr.delete_log_file(
    project="PCIe-Switch-FW",
    machine_ip="10.17.154.252",
    test_plan_id="TP-20260312-001",
    file_name="test_result.log",
    date_str="2026-03-12"
)
```

### 生成下载链接

```python
url = mgr.get_presigned_url(
    project="PCIe-Switch-FW",
    machine_ip="10.17.154.252",
    test_plan_id="TP-20260312-001",
    file_name="test_result.log",
    date_str="2026-03-12",
    expires_seconds=604800  # 7天有效期
)
```

## 路径规则

所有文件按照以下路径规则存储：

```
项目名/测试机器/日期/执行批次号/文件名
```

**示例：**
```
PCIe-Switch-FW/10.17.154.252/2026-03-12/TP-20260312-001/test_result.log
```

## API 参考

### MinioLogManager 类

#### 初始化

```python
MinioLogManager(
    endpoint: str = "10.17.154.252:9003",
    access_key: str = "admin",
    secret_key: str = "12345678",
    bucket_name: str = "auto-test-logs",
    secure: bool = False
)
```

#### 方法

| 方法 | 说明 | 适用场景 |
|------|------|----------|
| `upload_test_log()` | 普通上传 | 小文件（< 100MB） |
| `upload_large_file()` | 分块上传 | 大文件（>= 100MB） |
| `upload_log_auto()` | 智能上传 | 自动选择上传方式 |
| `upload_multiple_logs()` | 批量上传 | 多个文件 |
| `list_log_files()` | 列出文件 | 查询文件 |
| `delete_log_file()` | 删除文件 | 删除文件 |
| `get_presigned_url()` | 生成链接 | 下载文件 |

## 最佳实践

### 1. 选择合适的上传方式

```python
# 小文件：使用普通上传
mgr.upload_test_log(...)

# 大文件：使用智能上传（推荐）
mgr.upload_log_auto(...)

# 超大文件：显式使用分块上传，调整分块大小
mgr.upload_large_file(..., chunk_size=10 * 1024 * 1024)
```

### 2. 调整分块大小

根据网络状况和文件大小调整分块大小：

- **网络稳定**：使用较大的分块（10-20MB）
- **网络不稳定**：使用较小的分块（1-5MB）
- **超大文件**：使用中等分块（5-10MB）

```python
# 网络稳定环境
mgr.upload_large_file(..., chunk_size=20 * 1024 * 1024)

# 网络不稳定环境
mgr.upload_large_file(..., chunk_size=2 * 1024 * 1024)
```

### 3. 自定义大文件阈值

根据实际需求调整阈值：

```python
# 将阈值降低到 50MB
mgr.upload_log_auto(..., large_file_threshold=50 * 1024 * 1024)

# 将阈值提高到 200MB
mgr.upload_log_auto(..., large_file_threshold=200 * 1024 * 1024)
```

### 4. 错误处理

```python
try:
    url = mgr.upload_log_auto(
        project="PCIe-Switch-FW",
        machine_ip="10.17.154.252",
        test_plan_id="TP-20260312-001",
        local_file_path="./test.log"
    )
    
    if url:
        print(f"上传成功: {url}")
    else:
        print("上传失败")
        
except FileNotFoundError as e:
    print(f"文件不存在: {e}")
except Exception as e:
    print(f"上传出错: {e}")
```

## 性能优化

### 分块上传优势

1. **内存效率**：流式上传，不需要一次性加载整个文件到内存
2. **网络容错**：支持断点续传，网络中断后可以继续上传
3. **并发上传**：可以并发上传多个分块（需要自行实现）
4. **进度跟踪**：可以实时跟踪上传进度

### 性能对比

| 文件大小 | 普通上传 | 分块上传 | 推荐方式 |
|---------|---------|---------|---------|
| < 10MB | ✅ 快 | ❌ 慢 | 普通上传 |
| 10-100MB | ✅ 可用 | ✅ 可用 | 普通上传 |
| 100MB-1GB | ❌ 慢 | ✅ 快 | 分块上传 |
| > 1GB | ❌ 失败 | ✅ 快 | 分块上传 |

## 注意事项

1. **文件路径**：确保本地文件路径正确且可读
2. **网络连接**：确保能够访问 MinIO 服务器
3. **权限配置**：确保有足够的权限访问 Bucket
4. **存储空间**：确保 MinIO 服务器有足够的存储空间
5. **链接有效期**：预签名链接默认7天有效期，可根据需要调整

## 示例代码

完整示例请参考：
- [example_large_file_upload.py](./example_large_file_upload.py)

## 常见问题

### Q: 如何判断文件是否上传成功？

A: 检查返回值，成功返回下载链接，失败返回 None。

### Q: 分块上传失败会怎样？

A: 分块上传失败会自动清理已上传的分块，不会产生残留文件。

### Q: 如何调整上传速度？

A: 调整 `chunk_size` 参数，较大的分块通常有更好的吞吐量。

### Q: 支持断点续传吗？

A: 分块上传支持断点续传，但需要自行实现断点续传逻辑。

## 许可证

MIT License
