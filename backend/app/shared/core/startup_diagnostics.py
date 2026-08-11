"""Sanitized startup diagnostics for the active environment and dependencies."""

from urllib.parse import quote, urlsplit, urlunsplit

from app.shared.config import BootstrapSettings, RuntimeSettings, get_environment
from app.shared.core.logger import log


def mask_url_credentials(url: str) -> str:
    """Return a URL safe for logs, omitting credentials, query, and fragment."""
    parsed = urlsplit(url)
    netloc = parsed.netloc
    if "@" in netloc:
        _, _, hosts = netloc.rpartition("@")
        netloc = f"***:***@{hosts}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


def log_bootstrap_diagnostics(settings: BootstrapSettings) -> None:
    """Log environment and bootstrap endpoints before MongoDB is connected."""
    environment = get_environment()
    if environment in {"dev", "development"}:
        mode = "development"
    elif environment == "production":
        mode = "production"
    else:
        mode = environment
    log.debug(
        "启动环境 | service={} | environment={} | mode={} | app_debug={} | listen={}:{}",
        settings.app.service_name,
        environment,
        mode,
        settings.app.debug,
        settings.app.host,
        settings.app.port,
    )
    log.debug(
        "外部服务连接 | service=MongoDB | endpoint={} | database={}",
        mask_url_credentials(settings.mongodb.uri),
        settings.mongodb.db_name,
    )


def log_runtime_diagnostics(settings: RuntimeSettings) -> None:
    """Log sanitized endpoints from the activated MongoDB runtime settings."""
    rabbitmq = settings.rabbitmq
    rabbitmq_scheme = "amqps" if rabbitmq.ssl_enabled else "amqp"
    rabbitmq_vhost = quote(rabbitmq.virtual_host, safe="")
    log.debug(
        "外部服务连接 | service=RabbitMQ | endpoint={}://***:***@{}:{}/{}",
        rabbitmq_scheme,
        rabbitmq.host,
        rabbitmq.port,
        rabbitmq_vhost,
    )

    log.debug(
        "外部服务连接 | service=Kafka | bootstrap_servers={} | client_id={}",
        ",".join(settings.kafka.bootstrap_servers),
        settings.kafka.client_id,
    )

    minio_scheme = "https" if settings.minio.secure else "http"
    log.debug(
        "外部服务连接 | service=MinIO | endpoint={}://{} | bucket={}",
        minio_scheme,
        settings.minio.endpoint,
        settings.minio.bucket,
    )

    redis = settings.redis
    log.debug(
        "外部服务连接 | service=Redis Sentinel | sentinels={} | master={} | db={}",
        ",".join(redis.sentinel_hosts),
        redis.master_name,
        redis.db,
    )

    if settings.notification.enabled:
        log.debug(
            "外部服务连接 | service=Notification | endpoint={}",
            mask_url_credentials(settings.notification.guangquan.api_url),
        )
