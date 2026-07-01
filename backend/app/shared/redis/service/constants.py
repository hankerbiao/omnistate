"""Redis 模块常量。"""

# Key 命名空间
KEY_NAMESPACE = "dmlv4"

# 默认 Pub/Sub 频道
DEFAULT_EVENT_CHANNEL = "dmlv4:events"

# 发布队列最大容量
PUBLISH_QUEUE_MAXSIZE = 1000

# 服务注册 / 心跳相关配置
SERVICE_REGISTRY_TTL_SEC = 600  # 注册信息过期时间（秒），心跳续期需小于此值
HEARTBEAT_INTERVAL_SEC = 60     # 心跳续期间隔（秒）

# Sentinel 默认端口
DEFAULT_SENTINEL_PORT = 26379
