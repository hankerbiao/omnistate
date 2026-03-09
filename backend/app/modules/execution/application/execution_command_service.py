"""执行命令服务 - Phase 5

执行命令服务使用发件箱模式处理执行任务分发，
确保本地数据库事务与外部Kafka发布的可靠解耦。
"""

from typing import Any, Dict, Optional
from pymongo import AsyncMongoClient

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.test_specs.repository.models import TestCaseDoc
from app.shared.integration.outbox_service import OutboxService
from app.shared.core.logger import log as logger
from app.shared.core.mongo_client import get_mongo_client


class ExecutionCommandService:
    """执行命令服务

    负责处理执行任务分发的业务逻辑，使用发件箱模式确保可靠的外部事件发布。
    关键特点：
    - 所有写入操作在单个MongoDB事务中完成
    - Kafka发布通过outbox事件延迟执行
    - 支持重试机制和错误恢复
    """

    def __init__(self):
        """初始化执行命令服务"""
        self.outbox_service = OutboxService()

    async def dispatch_execution_task(
        self,
        command: DispatchExecutionTaskCommand,
        actor_id: str
    ) -> Dict[str, Any]:
        """分发执行任务

        使用发件箱模式处理任务分发，确保：
        1. 任务文档和outbox事件在同一事务中创建
        2. Kafka发布通过后台工作器异步处理
        3. 本地事务不依赖外部Kafka的可用性

        Args:
            command: 分发执行任务命令
            actor_id: 操作者ID（从JWT认证中获取）

        Returns:
            任务基本信息字典

        Raises:
            ValueError: 当命令验证失败时
            KeyError: 当测试用例不存在时
        """
        # ========== 步骤1: 验证命令 ==========
        validation_errors = command.validate()
        if validation_errors:
            raise ValueError(f"Command validation failed: {', '.join(validation_errors)}")

        # 验证actor_id与command.created_by一致（安全检查）
        if actor_id != command.created_by:
            logger.warning(f"Actor ID mismatch: actor={actor_id}, command.created_by={command.created_by}")
            raise ValueError("Actor identity mismatch")

        # ========== 步骤2: 验证测试用例存在 ==========
        case_ids = command.case_ids
        docs = await TestCaseDoc.find({
            "case_id": {"$in": case_ids},
            "is_deleted": False
        }).to_list()

        doc_map = {doc.case_id: doc for doc in docs}
        missing = [cid for cid in case_ids if cid not in doc_map]
        if missing:
            raise KeyError(f"Test cases not found: {missing}")

        # ========== 步骤3: 在单个事务中创建任务和outbox事件 ==========
        client: Optional[AsyncMongoClient] = get_mongo_client()
        if not client:
            raise RuntimeError("MongoDB client not available")

        def _is_transaction_not_supported(exc: Exception) -> bool:
            if hasattr(exc, 'message'):
                message = exc.message if isinstance(exc.message, str) else str(exc.message)
                return "transaction numbers are only allowed on a replica set member" in message
            return False

        try:
            async with client.start_session() as session:
                async with await session.start_transaction():
                    task_doc = ExecutionTaskDoc(
                        task_id=command.task_id,
                        external_task_id=command.external_task_id,
                        framework=command.framework,
                        dispatch_status="DISPATCHING",
                        overall_status="QUEUED",
                        request_payload=command.kafka_task_data,
                        dispatch_response=None,
                        dispatch_error=None,
                        created_by=command.created_by,
                        case_count=len(case_ids),
                        reported_case_count=0,
                    )
                    await task_doc.insert(session=session)

                    outbox_event = await self.outbox_service.create_execution_task_event(
                        task_id=command.task_id,
                        external_task_id=command.external_task_id,
                        kafka_task_data=command.kafka_task_data,
                        created_by=command.created_by,
                        session=session,
                    )

                    for cid in case_ids:
                        case_doc = doc_map[cid]
                        snapshot = {
                            "case_id": case_doc.case_id,
                            "title": case_doc.title,
                            "version": case_doc.version,
                            "priority": case_doc.priority,
                            "status": getattr(case_doc, 'status', '待执行'),
                        }

                        await ExecutionTaskCaseDoc(
                            task_id=command.task_id,
                            case_id=cid,
                            case_snapshot=snapshot,
                            status="QUEUED",
                            last_seq=0,
                        ).insert(session=session)

                    task_doc.dispatch_status = "CREATED"
                    task_doc.dispatch_response = {
                        "accepted": True,
                        "message": "Task created successfully, pending Kafka dispatch",
                        "outbox_event_id": outbox_event.event_id,
                    }
                    await task_doc.save(session=session)

                    logger.info(f"Successfully created task {command.task_id} with outbox event {outbox_event.event_id}")

        except Exception as e:
            if _is_transaction_not_supported(e):
                logger.error("MongoDB 部署不支持事务，已拒绝执行任务分发")
                raise RuntimeError("execution task dispatch requires MongoDB transaction support") from e
            logger.exception(f"Failed to create task {command.task_id}: {str(e)}")
            raise

        # ========== 步骤4: 返回任务信息 ==========
        # 返回基于本地创建的结果，不等待Kafka发布完成
        return {
            "task_id": task_doc.task_id,
            "external_task_id": task_doc.external_task_id,
            "dispatch_status": task_doc.dispatch_status,
            "overall_status": task_doc.overall_status,
            "case_count": task_doc.case_count,
            "created_at": task_doc.created_at,
            "outbox_event_id": outbox_event.event_id,
            "message": "Task created and queued for Kafka dispatch"
        }

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息

        Raises:
            KeyError: 当任务不存在时
        """
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        return {
            "task_id": task_doc.task_id,
            "external_task_id": task_doc.external_task_id,
            "dispatch_status": task_doc.dispatch_status,
            "overall_status": task_doc.overall_status,
            "case_count": task_doc.case_count,
            "created_at": task_doc.created_at,
            "updated_at": task_doc.updated_at,
            "dispatch_response": task_doc.dispatch_response,
            "dispatch_error": task_doc.dispatch_error,
        }

    async def retry_failed_task(self, task_id: str, actor_id: str) -> Dict[str, Any]:
        """重试失败的任务

        Args:
            task_id: 任务ID
            actor_id: 操作者ID

        Returns:
            重试结果

        Raises:
            KeyError: 当任务不存在时
            ValueError: 当任务状态不允许重试时
        """
        # 获取任务文档
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        # 检查任务状态是否允许重试
        if task_doc.dispatch_status not in ["DISPATCH_FAILED", "FAILED"]:
            raise ValueError(f"Task {task_id} cannot be retried in status {task_doc.dispatch_status}")

        # 创建新的outbox事件进行重试
        outbox_event = await self.outbox_service.create_execution_task_event(
            task_id=task_doc.task_id,
            external_task_id=task_doc.external_task_id,
            kafka_task_data=task_doc.request_payload,
            created_by=task_doc.created_by
        )

        # 更新任务状态
        task_doc.dispatch_status = "CREATED"
        task_doc.dispatch_error = None
        task_doc.dispatch_response = {
            "accepted": True,
            "message": "Task queued for retry",
            "outbox_event_id": outbox_event.event_id,
        }
        await task_doc.save()

        logger.info(f"Task {task_id} queued for retry with event {outbox_event.event_id}")

        return {
            "task_id": task_doc.task_id,
            "status": "retry_queued",
            "message": "Task queued for retry",
            "outbox_event_id": outbox_event.event_id
        }