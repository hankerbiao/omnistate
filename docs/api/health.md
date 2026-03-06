# 系统健康检查 API

## 概述

系统健康检查模块提供系统运行状态监控和服务健康检查功能。

**基础路径**: `/api/v1/health`

## 注意事项

- 健康检查接口通常不需要认证
- 用于监控系统状态和服务可用性

## 接口详情

### 系统健康检查

获取系统的整体健康状态。

```http
GET /api/v1/health
```

**认证**: 无需认证

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "status": "healthy",
    "timestamp": "2026-03-03T11:42:00Z",
    "uptime": 3600,
    "version": "1.0.0",
    "environment": "production",
    "services": {
      "database": {
        "status": "healthy",
        "response_time": 15,
        "last_check": "2026-03-03T11:42:00Z"
      },
      "cache": {
        "status": "healthy",
        "response_time": 5,
        "last_check": "2026-03-03T11:42:00Z"
      }
    },
    "system": {
      "cpu_usage": 25.5,
      "memory_usage": 68.2,
      "disk_usage": 45.1,
      "network_status": "connected"
    }
  }
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 系统总体状态：healthy/degraded/unhealthy |
| `timestamp` | string | 检查时间戳 |
| `uptime` | number | 系统运行时间（秒） |
| `version` | string | 应用版本号 |
| `environment` | string | 运行环境 |
| `services` | object | 各组件服务状态 |
| `system` | object | 系统资源使用情况 |

### 服务状态说明

| 状态 | 说明 |
|------|------|
| healthy | 服务正常运行 |
| degraded | 服务性能下降但可用 |
| unhealthy | 服务不可用或严重故障 |

### 系统状态值

| 状态值 | 说明 |
|--------|------|
| healthy | 所有组件正常 |
| degraded | 部分组件性能下降 |
| unhealthy | 系统不可用 |

## 详细检查

### 获取详细系统信息

```http
GET /api/v1/health/detailed
```

**认证**: 根据配置决定

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "status": "healthy",
    "timestamp": "2026-03-03T11:42:00Z",
    "build_info": {
      "version": "1.0.0",
      "build_time": "2026-03-03T10:00:00Z",
      "git_commit": "a1b2c3d",
      "build_branch": "main"
    },
    "database": {
      "status": "healthy",
      "type": "MongoDB",
      "version": "6.0.8",
      "connection_pool": {
        "active": 5,
        "idle": 15,
        "max": 100
      },
      "response_time": 15,
      "last_check": "2026-03-03T11:42:00Z"
    },
    "cache": {
      "status": "healthy",
      "type": "Redis",
      "version": "7.0.12",
      "memory_usage": "45MB",
      "key_count": 1250,
      "hit_rate": 0.85,
      "response_time": 5,
      "last_check": "2026-03-03T11:42:00Z"
    },
    "metrics": {
      "requests_per_minute": 150,
      "average_response_time": 120,
      "error_rate": 0.01,
      "active_connections": 25
    }
  }
}
```

### 获取组件状态

```http
GET /api/v1/health/components
```

**认证**: 根据配置决定

**响应示例**:
```json
{
  "code": 200,
  "message": "Success",
  "data": {
    "components": [
      {
        "name": "api_server",
        "status": "healthy",
        "response_time": 45,
        "last_check": "2026-03-03T11:42:00Z"
      },
      {
        "name": "mongodb",
        "status": "healthy",
        "response_time": 15,
        "last_check": "2026-03-03T11:42:00Z"
      },
      {
        "name": "redis",
        "status": "healthy",
        "response_time": 5,
        "last_check": "2026-03-03T11:42:00Z"
      },
      {
        "name": "workflow_engine",
        "status": "healthy",
        "response_time": 25,
        "last_check": "2026-03-03T11:42:00Z"
      }
    ]
  }
}
```

## 使用示例

### 基础健康检查

```bash
# 简单健康检查
curl -X GET "http://localhost:8000/api/v1/health"

# 获取详细系统信息
curl -X GET "http://localhost:8000/api/v1/health/detailed"

# 获取组件状态
curl -X GET "http://localhost:8000/api/v1/health/components"
```

### 监控脚本示例

```bash
#!/bin/bash
# 系统健康监控脚本

API_URL="http://localhost:8000/api/v1/health"
LOG_FILE="/var/log/health-check.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

check_health() {
    response=$(curl -s -w "%{http_code}" -o /tmp/health_response.json "$API_URL")
    http_code="${response: -3}"

    if [ "$http_code" -eq 200 ]; then
        status=$(jq -r '.data.status' /tmp/health_response.json)
        echo "[$TIMESTAMP] System status: $status" >> "$LOG_FILE"

        if [ "$status" = "healthy" ]; then
            echo "✅ System is healthy"
            exit 0
        else
            echo "⚠️  System status: $status"
            jq -r '.data' /tmp/health_response.json >> "$LOG_FILE"
            exit 1
        fi
    else
        echo "[$TIMESTAMP] Health check failed with HTTP $http_code" >> "$LOG_FILE"
        echo "❌ Health check failed"
        exit 2
    fi
}

check_health
```

### Docker 健康检查

```dockerfile
# Dockerfile 中的健康检查配置
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1
```

```yaml
# docker-compose.yml 中的健康检查
services:
  api:
    image: dmlv4-api:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
```

## 集成说明

### Prometheus 监控集成

```yaml
# prometheus.yml 配置
scrape_configs:
  - job_name: 'dmlv4-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/v1/health'
    scrape_interval: 30s
```

### Grafana 仪表板指标

| 指标名称 | 类型 | 说明 |
|----------|------|------|
| api_health_status | Gauge | API健康状态 (0/1) |
| api_response_time | Histogram | API响应时间 |
| db_connection_pool | Gauge | 数据库连接池状态 |
| memory_usage_percent | Gauge | 内存使用百分比 |
| cpu_usage_percent | Gauge | CPU使用百分比 |

### Kubernetes 健康探针

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: dmlv4-api
    image: dmlv4-api:latest
    livenessProbe:
      httpGet:
        path: /api/v1/health
        port: 8000
      initialDelaySeconds: 60
      periodSeconds: 30
    readinessProbe:
      httpGet:
        path: /api/v1/health
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
```

## 最佳实践

### 监控策略
1. 定期执行健康检查
2. 设置合理的阈值和告警
3. 记录历史监控数据
4. 建立告警通知机制

### 性能考虑
1. 健康检查接口要轻量级
2. 避免对系统造成额外负担
3. 合理设置检查频率
4. 缓存检查结果

### 运维建议
1. 将健康检查集成到部署流程
2. 设置服务依赖关系监控
3. 建立多层次健康检查
4. 定期审查监控策略