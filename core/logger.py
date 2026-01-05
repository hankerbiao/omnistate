import sys
import os
from loguru import logger

# 日志目录设置
LOG_DIR = os.path.join(os.getcwd(), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 日志格式定义
# <green> 等标签是 loguru 特有的彩色输出
# {time} 时间, {level} 等级, {file}:{line} 文件和行号, {message} 内容
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{file}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

def setup_logger(console_level="DEBUG"):
    """
    统一配置日志模块
    - console_level: 控制台输出等级，默认为 DEBUG
    """
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
    # INFO 及以上级别的日志 (包含 INFO, WARNING, ERROR, CRITICAL)
    logger.add(
        os.path.join(LOG_DIR, "info.log"),
        level="INFO",
        format=LOG_FORMAT,
        rotation="10 MB",      # 文件超过 10MB 自动切割
        retention="1 week",    # 保留一周
        encoding="utf-8",
        enqueue=True           # 异步写入，提升性能
    )

    # ERROR 及以上级别的日志 (包含 ERROR, CRITICAL)
    # 专门记录错误，方便排查
    logger.add(
        os.path.join(LOG_DIR, "error.log"),
        level="ERROR",
        format=LOG_FORMAT,
        rotation="10 MB",
        retention="1 month",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,        # 记录完整的异常堆栈
        diagnose=True          # 记录变量值，极大方便调试
    )

    # DEBUG 级别的日志单独记录
    logger.add(
        os.path.join(LOG_DIR, "debug.log"),
        level="DEBUG",
        format=LOG_FORMAT,
        rotation="10 MB",
        retention="3 days",
        encoding="utf-8",
        filter=lambda record: record["level"].name == "DEBUG" # 仅记录 DEBUG
    )

    return logger

# 初始化全局 logger
log = setup_logger()
