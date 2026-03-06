from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient
from beanie import init_beanie

from app.shared.api.errors.handlers import setup_exception_handlers
from app.shared.api.main import api_router
from app.shared.db.config import settings
from app.shared.core.logger import log
from app.shared.core.mongo_client import set_mongo_client

from app.modules.workflow.repository.models import (
    SysWorkTypeDoc, SysWorkflowStateDoc, SysWorkflowConfigDoc,
    BusWorkItemDoc, BusFlowLogDoc
)
from app.modules.assets.repository.models import (
    ComponentLibraryDoc,
    DutDoc,
    TestPlanComponentDoc,
)
from app.modules.test_specs.repository.models import (
    TestRequirementDoc,
    TestCaseDoc,
    AutomationTestCaseDoc,
)
from app.modules.execution.repository.models import (
    ExecutionTaskDoc,
    ExecutionTaskCaseDoc,
    ExecutionEventDoc,
)
from app.modules.execution.service.execution_service import ExecutionService
from app.modules.auth.repository.models import UserDoc, RoleDoc, PermissionDoc, NavigationPageDoc


async def validate_workflow_consistency() -> None:
    """启动时校验 workflow 基础配置，避免脏配置进入运行期。"""
    work_types = await SysWorkTypeDoc.find_all().to_list()
    states = await SysWorkflowStateDoc.find_all().to_list()
    configs = await SysWorkflowConfigDoc.find_all().to_list()

    # 对未初始化环境做兼容：仅告警，不阻断服务启动。
    if not work_types and not states and not configs:
        log.warning("workflow consistency check skipped: workflow configs are empty, run `python app/init_mongodb.py` to initialize")
        return

    if not work_types:
        raise RuntimeError("workflow consistency check failed: no work types configured")
    if not states:
        raise RuntimeError("workflow consistency check failed: no states configured")

    type_codes = {doc.code for doc in work_types}
    state_codes = {doc.code for doc in states}
    errors: list[str] = []

    for cfg in configs:
        if cfg.type_code not in type_codes:
            errors.append(f"unknown type_code={cfg.type_code}")
        if cfg.from_state not in state_codes:
            errors.append(f"unknown from_state={cfg.from_state}")
        if cfg.to_state not in state_codes:
            errors.append(f"unknown to_state={cfg.to_state}")

    if errors:
        raise RuntimeError(
            "workflow consistency check failed: " + "; ".join(sorted(set(errors)))
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用生命周期钩子：统一管理 Mongo 连接和 Beanie 初始化
    log.info("正在连接 MongoDB...")

    client = AsyncMongoClient(settings.MONGO_URI)

    try:
        await client.admin.command('ping')
        log.success("MongoDB 连接成功")

        # 注入全局 Mongo 客户端，供需要底层访问或事务的代码使用
        set_mongo_client(client)

        # 初始化 Beanie ODM，注册所有文档模型并确保索引
        await init_beanie(
            database=client[settings.MONGO_DB_NAME],
            document_models=[
                SysWorkTypeDoc,
                SysWorkflowStateDoc,
                SysWorkflowConfigDoc,
                BusWorkItemDoc,
                BusFlowLogDoc,
                ComponentLibraryDoc,
                DutDoc,
                TestPlanComponentDoc,
                TestRequirementDoc,
                TestCaseDoc,
                AutomationTestCaseDoc,
                ExecutionTaskDoc,
                ExecutionTaskCaseDoc,
                ExecutionEventDoc,
                UserDoc,
                RoleDoc,
                PermissionDoc,
                NavigationPageDoc,
            ]
        )
        log.success("Beanie ODM 初始化完成")
        await validate_workflow_consistency()
        log.success("Workflow 配置一致性校验通过")
        #
        # 启动Kafka执行任务监听器
        try:
            execution_service = ExecutionService()
            log.success("Kafka 准备启动")
            await execution_service.start_kafka_listener()
            log.success("Kafka 执行任务监听器启动成功")
        except Exception as e:
            log.error(f"Failed to start Kafka listener: {e}")

        log.success("FastAPI 服务启动完成")
        yield
    finally:
        log.info("FastAPI 服务已关闭")

        # 关闭Kafka连接
        try:
            if 'execution_service' in locals():
                execution_service.kafka_manager.stop()
                log.info("Kafka manager stopped")
        except Exception as e:
            log.error(f"Error stopping Kafka manager: {e}")

        if client:
            close_result = client.close()
            if hasattr(close_result, "__await__"):
                await close_result
        set_mongo_client(None)
        log.info("MongoDB 连接已关闭")


app = FastAPI(
    title="Workflow API (MongoDB)",
    description="配置驱动的工作流状态机服务 - MongoDB 版本",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 与中间件、错误处理和业务路由都在这里统一挂载
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_exception_handlers(app)

app.include_router(api_router)


if __name__ == "__main__":
    import asyncio
    import sys
    import uvicorn

    try:
        # 首先尝试原始方式
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except TypeError as e:
        if "loop_factory" in str(e):
            print(f"⚠️  检测到Python 3.13兼容性问题，使用修复模式启动...")
            print(f"🔧 错误详情: {e}")

            # Python 3.13兼容方式：手动创建服务器并启动
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=8000,
                log_level="info",
                access_log=True
            )
            server = uvicorn.Server(config)

            # 在Python 3.13中使用兼容的启动方式
            if sys.version_info >= (3, 13):
                # 直接调用serve方法而不是通过asyncio.run
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(server.serve())
                finally:
                    loop.close()
            else:
                # 旧版本Python
                asyncio.run(server.serve())

        else:
            # 其他TypeError，重新抛出
            raise
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        raise
