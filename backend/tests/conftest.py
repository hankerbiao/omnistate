import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.api.errors.handlers import setup_exception_handlers
from app.shared.api.main import api_router


@pytest.fixture()
def app():
    # 创建一个最小可运行的 FastAPI 应用实例，用于测试 API 行为
    app = FastAPI()
    # 注册全局异常处理器，确保测试断言的是统一的错误返回结构
    setup_exception_handlers(app)
    # 加载项目的 API 路由（包含健康检查与业务接口）
    app.include_router(api_router)
    return app


@pytest.fixture()
def client(app):
    # 为测试提供 HTTP 客户端，便于发起同步请求
    return TestClient(app)
