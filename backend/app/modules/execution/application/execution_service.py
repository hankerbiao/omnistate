"""执行命令服务。"""

from typing import Any, Dict

from app.modules.execution.application.commands import DispatchExecutionTaskCommand
from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.test_specs.repository.models import TestCaseDoc
from app.shared.core.logger import log as logger
from app.shared.infrastructure import get_kafka_manager
from app.shared.kafka import TaskMessage


class ExecutionService:
    """执行任务分发服务。"""

    async def dispatch_execution_task(
        self,
        command: DispatchExecutionTaskCommand,
        actor_id: str
    ) -> Dict[str, Any]:
        """分发执行任务。"""
        validation_errors = command.validate()
        if validation_errors:
            raise ValueError(f"Command validation failed: {', '.join(validation_errors)}")

        if actor_id != command.created_by:
            logger.warning(f"Actor ID mismatch: actor={actor_id}, command.created_by={command.created_by}")
            raise ValueError("Actor identity mismatch")

        case_ids = command.case_ids
        docs = await TestCaseDoc.find({
            "case_id": {"$in": case_ids},
            "is_deleted": False
        }).to_list()

        doc_map = {doc.case_id: doc for doc in docs}
        missing = [cid for cid in case_ids if cid not in doc_map]
        if missing:
            raise KeyError(f"Test cases not found: {missing}")

        task_doc = ExecutionTaskDoc(
            task_id=command.task_id,
            external_task_id=command.external_task_id,
            framework=command.framework,
            dispatch_status="DISPATCHING",
            overall_status="QUEUED",
            request_payload=command.kafka_task_data,
            dispatch_response={},
            dispatch_error=None,
            created_by=command.created_by,
            case_count=len(case_ids),
            reported_case_count=0,
        )
        await task_doc.insert()

        for cid in case_ids:
            case_doc = doc_map[cid]
            snapshot = {
                "case_id": case_doc.case_id,
                "title": case_doc.title,
                "version": case_doc.version,
                "priority": case_doc.priority,
                "status": getattr(case_doc, "status", "待执行"),
            }

            await ExecutionTaskCaseDoc(
                task_id=command.task_id,
                case_id=cid,
                case_snapshot=snapshot,
                status="QUEUED",
                last_seq=0,
            ).insert()

        kafka_manager = get_kafka_manager()
        if not kafka_manager:
            task_doc.dispatch_status = "DISPATCH_FAILED"
            task_doc.dispatch_error = "Kafka manager not available"
            task_doc.dispatch_response = {
                "accepted": False,
                "message": "Kafka manager not available",
            }
            await task_doc.save()
            raise ValueError("Kafka manager not available")

        task_message = TaskMessage(
            task_id=command.task_id,
            task_type="execution_task",
            task_data=command.kafka_task_data,
            source="dmlv4-execution-api",
            priority=1,
        )
        success = kafka_manager.send_task(task_message)

        if success:
            task_doc.dispatch_status = "DISPATCHED"
            task_doc.dispatch_response = {
                "accepted": True,
                "message": "Task dispatched to Kafka successfully",
            }
            logger.info(f"Successfully dispatched task {command.task_id} to Kafka")
        else:
            task_doc.dispatch_status = "DISPATCH_FAILED"
            task_doc.dispatch_error = "Failed to send task to Kafka"
            task_doc.dispatch_response = {
                "accepted": False,
                "message": "Failed to dispatch task to Kafka",
            }
            logger.warning(f"Failed to dispatch task {command.task_id} to Kafka")

        await task_doc.save()
        return {
            "task_id": task_doc.task_id,
            "external_task_id": task_doc.external_task_id,
            "dispatch_status": task_doc.dispatch_status,
            "overall_status": task_doc.overall_status,
            "case_count": task_doc.case_count,
            "created_at": task_doc.created_at,
            "message": task_doc.dispatch_response.get("message", ""),
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
        """重试失败的任务。"""
        task_doc = await ExecutionTaskDoc.find_one({"task_id": task_id})
        if not task_doc:
            raise KeyError(f"Task not found: {task_id}")

        if task_doc.dispatch_status not in ["DISPATCH_FAILED", "FAILED"]:
            raise ValueError(f"Task {task_id} cannot be retried in status {task_doc.dispatch_status}")

        if actor_id != task_doc.created_by:
            logger.warning(f"Actor ID mismatch on retry: actor={actor_id}, task.created_by={task_doc.created_by}")
            raise ValueError("Actor identity mismatch")

        kafka_manager = get_kafka_manager()
        if not kafka_manager:
            raise ValueError("Kafka manager not available")

        task_message = TaskMessage(
            task_id=task_doc.task_id,
            task_type="execution_task",
            task_data=task_doc.request_payload,
            source="dmlv4-execution-api",
            priority=1,
        )
        success = kafka_manager.send_task(task_message)

        task_doc.dispatch_status = "DISPATCHED" if success else "DISPATCH_FAILED"
        task_doc.dispatch_error = None if success else "Failed to send task to Kafka"
        task_doc.dispatch_response = {
            "accepted": success,
            "message": "Task retried successfully" if success else "Failed to dispatch task to Kafka",
        }
        await task_doc.save()

        if success:
            logger.info(f"Task {task_id} retried successfully")
        else:
            logger.warning(f"Task {task_id} retry failed")

        return {
            "task_id": task_doc.task_id,
            "status": "retried" if success else "retry_failed",
            "message": task_doc.dispatch_response["message"],
        }
