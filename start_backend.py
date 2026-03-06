#!/usr/bin/env python3
"""
DMLV4 后端启动脚本 - Python 3.13兼容版本

修复了uvicorn在Python 3.13中的兼容性问题。
"""

import asyncio
import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def start_server():
    """启动FastAPI服务器"""
    import uvicorn
    from app.main import app  # 假设app对象在main.py中定义

    print(f"🚀 DMLV4 后端启动中...")
    print(f"🐍 Python版本: {sys.version}")
    print(f"📍 监听地址: http://0.0.0.0:8000")

    # 检查Python版本并选择合适的启动方式
    if sys.version_info >= (3, 13):
        print("🔧 检测到Python 3.13，使用兼容启动模式")

        # Python 3.13兼容启动
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True,
            reload=False  # 开发模式下关闭热重载避免问题
        )
        server = uvicorn.Server(config)

        # 手动管理事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server.serve())
        except KeyboardInterrupt:
            print("\n🛑 服务器已停止")
        finally:
            loop.close()
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}，使用标准启动模式")
        # 旧版本Python使用标准方式
        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)