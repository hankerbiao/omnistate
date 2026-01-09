"""全局配置"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
from loguru import logger
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time}</green> | {message}")

# 导入 fixtures（确保 pytest 能找到它们）
from pytest_server_test.fixtures import *