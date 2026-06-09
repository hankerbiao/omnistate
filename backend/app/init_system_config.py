"""
初始化系统配置默认数据

运行此脚本可以初始化默认配置项（如果不存在）
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def init_system_configs():
    """初始化系统配置"""
    from app.shared.db.connection import get_database
    from app.modules.system_config.service import ConfigService

    # 连接数据库
    db = await get_database()

    # 初始化默认配置
    await ConfigService.init_default_configs()

    print("系统配置初始化完成")
    print("\n默认配置项:")
    for config in ConfigService.DEFAULT_CONFIGS:
        print(f"  - {config['config_key']}: {config['config_value']}")


if __name__ == "__main__":
    asyncio.run(init_system_configs())