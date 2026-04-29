"""日志配置模块。

日志配置可从 config.yaml 读取，也支持默认值。
注意：此模块在配置加载之前被部分引用，因此使用 try-except 处理配置不存在的情况。
"""

import os
import sys
from loguru import logger

# 日志目录设置（基于项目根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DEFAULT_LOG_DIR = os.path.join(BASE_DIR, "logs")

# 日志格式定义
# <green> 等标签是 loguru 特有的彩色输出
# {time} 时间, {level} 等级, {file}:{line} 文件和行号, {message} 内容
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{file}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)


def _load_log_config() -> dict:
    """尝试从配置加载日志配置，失败时使用默认值。"""
    try:
        from app.shared.config import get_settings
        settings = get_settings()
        return {
            "console_level": settings.logging.console_level,
            "log_dir": settings.logging.log_dir,
            "info_days": settings.logging.retention.info_days,
            "error_days": settings.logging.retention.error_days,
            "debug_days": settings.logging.retention.debug_days,
        }
    except Exception:
        # 配置加载失败时使用默认值
        return {
            "console_level": "DEBUG",
            "log_dir": DEFAULT_LOG_DIR,
            "info_days": 7,
            "error_days": 30,
            "debug_days": 3,
        }


def setup_logger(console_level: str | None = None) -> logger:
    """
    统一配置日志模块

    Args:
        console_level: 控制台输出等级，默认为从配置读取或 DEBUG
    """
    # 加载日志配置
    log_config = _load_log_config()

    if console_level is None:
        console_level = log_config["console_level"]

    log_dir = log_config["log_dir"]

    # 确保日志目录存在
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 移除默认的 handler
    logger.remove()

    # 1. 配置控制台输出
    logger.add(
        sys.stdout,
        level=console_level,
        format=LOG_FORMAT,
        colorize=True
    )

    # 2. 配置文件输出 - 分级别记录
    # INFO 及以上级别的日志
    logger.add(
        os.path.join(log_dir, "info.log"),
        level="INFO",
        format=LOG_FORMAT,
        rotation="10 MB",
        retention=f"{log_config['info_days']} days",
        encoding="utf-8",
        enqueue=True
    )

    # ERROR 及以上级别的日志
    logger.add(
        os.path.join(log_dir, "error.log"),
        level="ERROR",
        format=LOG_FORMAT,
        rotation="10 MB",
        retention=f"{log_config['error_days']} days",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True
    )

    # DEBUG 级别的日志单独记录
    logger.add(
        os.path.join(log_dir, "debug.log"),
        level="DEBUG",
        format=LOG_FORMAT,
        rotation="10 MB",
        retention=f"{log_config['debug_days']} days",
        encoding="utf-8",
        filter=lambda record: record["level"].name == "DEBUG"
    )

    return logger


# 初始化全局 logger
log = setup_logger()