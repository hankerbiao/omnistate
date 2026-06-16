"""统一日志配置模块。

结构化日志系统，支持：
- JSON Lines 格式输出（文件），彩色文本输出（控制台）
- 自动 .gz 压缩轮转
- contextvars 追踪上下文注入（request_id, user_id, client_ip）
- 敏感数据脱敏（token, password, secret等）
- 健康检查等噪音日志过滤
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

from loguru import logger

from app.shared.config import get_settings

# =============================================================================
# 敏感数据脱敏规则
# =============================================================================
SENSITIVE_FIELDS = {
    "password", "passwd", "secret", "token", "access_token",
    "refresh_token", "api_key", "apikey", "authorization",
    "jwt", "private_key", "credential",
}

SENSITIVE_PATTERN = re.compile(
    r'(?i)(' + '|'.join(SENSITIVE_FIELDS) + r')\s*[=:]\s*["\']?[^\s,;&"\']+["\']?'
)

PASSWORD_REPLACEMENT = r'\1=******'

# =============================================================================
# 日志目录
# =============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
DEFAULT_LOG_DIR = os.path.join(BASE_DIR, "logs")


def _load_log_config() -> dict[str, Any]:
    """从配置加载日志设置，失败时使用默认值。"""
    try:
        settings = get_settings()
        lc = settings.logging
        return {
            "console_level": lc.console_level,
            "log_dir": lc.log_dir,
            "json_format": getattr(lc, "json_format", True),
            "enable_compress": getattr(lc, "enable_compress", True),
            "info_days": lc.retention.info_days,
            "error_days": lc.retention.error_days,
            "debug_days": lc.retention.debug_days,
            "slow_query_threshold_ms": getattr(lc, "slow_query_threshold_ms", 200),
            "module_levels": getattr(lc, "module_levels", {}),
        }
    except Exception:
        return {
            "console_level": "DEBUG",
            "log_dir": DEFAULT_LOG_DIR,
            "json_format": True,
            "enable_compress": True,
            "info_days": 7,
            "error_days": 30,
            "debug_days": 3,
            "slow_query_threshold_ms": 200,
            "module_levels": {},
        }


# =============================================================================
# 追踪上下文提取器（从 contextvars 读取，避免模块循环导入）
# =============================================================================
# 使用惰性导入方案：在 format 函数中按需导入 context
# 避免 logger.py → context.py 的循环依赖

# loguru record["extra"] 内置键，不重复写入 JSON context
_LOGURU_EXTRA_SKIP = frozenset({
    "color_message", "elapsed", "exception", "extra", "file", "function",
    "level", "line", "message", "module", "name", "process", "thread",
    "time",
})


def _get_trace_extra() -> dict[str, str]:
    """从异步上下文提取追踪与操作者信息，作为日志 extra 字段。"""
    try:
        from app.shared.context import get_operation_context, get_trace_context
        trace = get_trace_context()
        operation = get_operation_context()
        return {
            "request_id": trace.request_id or "-",
            "trace_id": trace.trace_id or "-",
            "client_ip": trace.client_ip or "-",
            "user_id": operation.actor_id or "-",
            "username": operation.username or "-",
        }
    except Exception:
        return {
            "request_id": "-",
            "trace_id": "-",
            "client_ip": "-",
            "user_id": "-",
            "username": "-",
        }


def _merge_execution_extra() -> dict[str, str]:
    """从 execution 业务上下文提取字段。"""
    try:
        from app.modules.execution.shared.execution_context import get_execution_context
        ctx = get_execution_context()
        return {
            "task_id": ctx.task_id or "-",
            "case_id": ctx.case_id or "-",
            "event_id": ctx.event_id or "-",
            "agent_id": ctx.agent_id or "-",
            "node": ctx.node or "-",
        }
    except Exception:
        return {
            "task_id": "-",
            "case_id": "-",
            "event_id": "-",
            "agent_id": "-",
            "node": "-",
        }


def _enrich_record(record: dict) -> None:
    """向 record.extra 注入追踪上下文和执行上下文。"""
    for key, value in {**_get_trace_extra(), **_merge_execution_extra()}.items():
        record["extra"].setdefault(key, value)


def _truncate_json_value(value: Any, max_chars: int = 2048) -> Any:
    """截断过大的 extra 字段值。"""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    import json
    try:
        serialized = json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        serialized = str(value)
    if len(serialized) <= max_chars:
        return value
    return f"{serialized[:max_chars]}...(truncated)"


def _mask_sensitive_data(message: str) -> str:
    """对日志消息中的敏感字段进行脱敏处理。"""
    return SENSITIVE_PATTERN.sub(PASSWORD_REPLACEMENT, message)


def _console_id(value: str, *, empty: str = "-") -> str:
    """控制台追踪 ID：无上下文时为短占位符，有值时截断避免撑满一行。"""
    text = str(value or "").strip()
    if not text or text == "-":
        return empty
    return text if len(text) <= 12 else f"{text[:12]}…"


# =============================================================================
# 控制台输出格式（彩色可读）
# =============================================================================
CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[request_id]}</cyan> | "
    "<cyan>{extra[user_id]}</cyan> | "
    "<cyan>{file}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n"
)


def _console_format(record: dict) -> str:
    """控制台格式化器：动态注入追踪上下文并脱敏。

    可调用 format 不会自动补换行，模板末尾必须包含 \\n。
    """
    _enrich_record(record)
    record["extra"]["request_id"] = _console_id(record["extra"].get("request_id", "-"))
    record["extra"]["user_id"] = _console_id(record["extra"].get("user_id", "-"))
    record["message"] = _mask_sensitive_data(str(record["message"]))
    return CONSOLE_FORMAT


# =============================================================================
# JSON 格式序列化器
# =============================================================================
def _json_format(record: dict) -> str:
    """JSON Lines 格式化：每条日志输出为一行 JSON。"""
    _enrich_record(record)

    log_entry: dict[str, Any] = {
        "timestamp": record.get("time", None),
        "level": record["level"].name,
        "module": record.get("name", ""),
        "function": record.get("function", ""),
        "line": record.get("line", 0),
        "message": _mask_sensitive_data(str(record.get("message", ""))),
        "request_id": record["extra"].get("request_id", "-"),
        "user_id": record["extra"].get("user_id", "-"),
        "trace_id": record["extra"].get("trace_id", "-"),
        "client_ip": record["extra"].get("client_ip", "-"),
    }

    base_keys = set(log_entry.keys())
    for key, value in record["extra"].items():
        if key in _LOGURU_EXTRA_SKIP or key in base_keys:
            continue
        if value is None or value == "-":
            continue
        log_entry[key] = _truncate_json_value(value)

    if record["level"].name in ("ERROR", "CRITICAL"):
        if exception := record.get("exception"):
            log_entry["exception"] = {
                "type": exception.type.__name__ if exception.type else "",
                "value": str(exception.value) if exception.value else "",
                "traceback": exception.traceback if hasattr(exception, "traceback") and exception.traceback else "",
            }

    # format 可调用对象必须返回「模板字符串」，不能返回已格式化的 JSON；
    # 否则 Loguru 会把 JSON 里的 {"timestamp": ...} 当成占位符再次 format，触发 KeyError。
    record["message"] = json.dumps(log_entry, default=str, ensure_ascii=False)
    return "{message}\n"


# =============================================================================
# 健康检查过滤
# =============================================================================
def _is_health_check(record: dict) -> bool:
    """过滤健康检查的噪音日志。"""
    message = record.get("message", "")
    if "/health" in message and record["level"].name == "DEBUG":
        return False
    return True


def _is_execution_domain(record: dict) -> bool:
    """仅保留 execution 域结构化日志。"""
    return record["extra"].get("domain") == "execution"


def _build_module_level_filter(module_levels: dict[str, str]):
    """按模块路径前缀过滤低于配置级别的日志。"""
    if not module_levels:
        return _is_health_check

    thresholds = {
        prefix: logger.level(level_name).no
        for prefix, level_name in module_levels.items()
    }

    def combined_filter(record: dict) -> bool:
        if not _is_health_check(record):
            return False
        module_name = record.get("name", "")
        for prefix, min_level_no in thresholds.items():
            if module_name.startswith(prefix):
                return record["level"].no >= min_level_no
        return True

    return combined_filter


# =============================================================================
# 日志设置
# =============================================================================
def setup_logger() -> logger:
    """统一配置日志系统。

    输出目标：
      1. 控制台 — 彩色可读，注入追踪上下文，脱敏
      2. app.log — JSON Lines 全量日志，自动 .gz 轮转
      3. error.log — JSON Lines ERROR+ 级别日志，自动 .gz 轮转
    """
    log_config = _load_log_config()
    log_dir = log_config["log_dir"]

    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    # 移除默认 handler
    logger.remove()

    module_levels = log_config.get("module_levels") or {}
    combined_filter = _build_module_level_filter(module_levels)

    # 1. 控制台输出
    logger.add(
        sys.stdout,
        level=log_config["console_level"],
        format=_console_format,
        colorize=True,
        filter=combined_filter,
    )

    # 2. JSON Lines 全量日志
    compression = "gz" if log_config["enable_compress"] else None
    logger.add(
        os.path.join(log_dir, "app.log"),
        level="DEBUG",
        format=_json_format,
        rotation="50 MB",
        retention=f"{log_config['info_days']} days",
        compression=compression,
        encoding="utf-8",
        enqueue=True,
        filter=combined_filter,
    )

    # 3. execution 域独立日志（便于 tail 排障）
    logger.add(
        os.path.join(log_dir, "execution.log"),
        level="DEBUG",
        format=_json_format,
        rotation="50 MB",
        retention=f"{log_config['info_days']} days",
        compression=compression,
        encoding="utf-8",
        enqueue=True,
        filter=lambda record: combined_filter(record) and _is_execution_domain(record),
    )

    # 4. ERROR+ 级别独立日志
    logger.add(
        os.path.join(log_dir, "error.log"),
        level="ERROR",
        format=_json_format,
        rotation="50 MB",
        retention=f"{log_config['error_days']} days",
        compression=compression,
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    return logger


# =============================================================================
# 全局日志实例
# =============================================================================
log = setup_logger()
