"""
测试执行服务模块 - 仅保留下发任务接口

该模块负责与外部测试框架集成，处理测试任务的创建和分发。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.modules.execution.repository.models import (
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.test_specs.repository.models import TestCaseDoc
from app.shared.kafka import KafkaMessageManager, TaskMessage
from app.shared.service import BaseService, SequenceIdService


class ExecutionService(BaseService):
    """
    执行任务分发服务。

    该服务负责接收并分发测试任务到外部测试框架。
    """

    def __init__(self):
        """初始化执行服务。"""
        super().__init__()
        self.kafka_manager = KafkaMessageManager()

    async def dispatch_task(self, payload: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """
        创建并分发测试任务到外部测试框架。

        这是任务创建的入口方法，执行以下步骤：
        1. 验证请求参数的有效性（用例列表、case_id等）
        2. 验证所有用例在数据库中存在且未被删除
        3. 生成唯一的任务ID和外部任务ID
        4. 准备Kafka消息所需的任务数据
        5. 保存任务文档到数据库
        6. 将任务发送到Kafka队列
        7. 为每个用例创建任务用例记录
        8. 更新任务状态并返回结果

        Args:
            payload: 任务创建请求负载，包含：
                - cases: 用例ID列表，每个元素包含case_id
                - framework: 测试框架类型
                - trigger_source: 任务触发来源
                - callback_url: 回调URL（可选）
                - dut: 设备配置信息（可选）
                - runtime_config: 运行时配置（可选）
            created_by: 创建任务的用户ID

        Returns:
            包含任务基本信息的字典：
                - task_id: 内部任务ID
                - external_task_id: 外部任务ID（用于测试框架识别）
                - dispatch_status: 任务下发状态
                - overall_status: 任务整体状态
                - case_count: 包含的用例数量
                - created_at: 创建时间

        Raises:
            ValueError: 当用例列表为空、缺少case_id或有重复case_id时
            KeyError: 当某些case_id在数据库中不存在时
            ValueError: 当Kafka消息发送失败时
        """
        # ========== 步骤1: 验证用例列表 ==========
        # 从请求负载中提取用例列表，如果为空则使用空列表
        cases = payload.get("cases") or []
        # 验证用例列表不能为空
        if not cases:
            raise ValueError("cases must not be empty")

        # 提取所有case_id并去除空格，确保为字符串类型
        # 例如：["TC001", "TC002", "TC003"]
        case_ids = [str(item.get("case_id", "")).strip() for item in cases]
        # 验证所有case_id都不为空（防止空字符串）
        if not all(case_ids):
            raise ValueError("case_id is required")
        # 验证case_id没有重复（使用集合比较长度）
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("duplicate case_id in request")

        # ========== 步骤2: 验证用例在数据库中存在且未被软删除 ==========
        # 使用MongoDB的$in操作符批量查询所有用例，提升查询效率
        # 过滤条件：case_id在请求列表中 AND 未被软删除
        docs = await TestCaseDoc.find(
            {"case_id": {"$in": case_ids}, "is_deleted": False}
        ).to_list()
        # 构建case_id到文档对象的映射，便于快速查找
        # 例如：{"TC001": <TestCaseDoc>, "TC002": <TestCaseDoc>, ...}
        doc_map = {doc.case_id: doc for doc in docs}
        # 检查是否有缺失的case_id（请求的用例在数据库中不存在）
        missing = [cid for cid in case_ids if cid not in doc_map]
        if missing:
            raise KeyError(f"case not found: {missing}")

        # ========== 步骤3: 生成任务ID ==========
        # 内部任务ID格式：ET-YYYY-XXXXXX
        # 例如：ET-2026-000001 (2026年第1个任务)
        year = datetime.now().year
        # 获取当年任务序列号（自增，保证唯一性）
        seq = await SequenceIdService().next(f"execution_task:{year}")
        # 格式化：6位序列号，左侧补零
        task_id = f"ET-{year}-{str(seq).zfill(6)}"
        # 外部任务ID格式：EXT-ET-YYYY-XXXXXX (供外部测试框架识别)
        external_task_id = f"EXT-{task_id}"

        # ========== 步骤4: 准备Kafka任务数据 ==========
        # 构建将发送到外部测试框架的任务数据
        # 外部框架将根据这些数据执行测试任务
        kafka_task_data = {
            "task_id": task_id,                    # 内部任务ID
            "external_task_id": external_task_id,  # 外部任务ID
            "framework": payload.get("framework"), # 测试框架类型（如pytest, jtest等）
            "trigger_source": payload.get("trigger_source"),  # 任务触发来源（API/UI/CI等）
            "callback_url": payload.get("callback_url"),      # 回调URL（可选）
            "dut": payload.get("dut") or {},       # 被测设备配置（可选）
            # 简化的用例列表（只包含case_id，完整信息从数据库获取）
            "cases": [{"case_id": cid} for cid in case_ids],
            "runtime_config": payload.get("runtime_config") or {},  # 运行时配置（可选）
            "created_by": created_by,              # 任务创建者ID
            "created_at": datetime.now(timezone.utc).isoformat(),  # UTC时间戳
        }

        # ========== 步骤5: 保存任务记录到数据库 ==========
        # 创建任务文档对象，初始状态为"正在下发"和"等待执行"
        # 使用insert()而不是save()，因为是新文档
        task_doc = ExecutionTaskDoc(
            task_id=task_id,
            external_task_id=external_task_id,
            framework=str(payload.get("framework") or "unknown"),
            dispatch_status="DISPATCHING",  # 任务下发状态：正在下发
            overall_status="QUEUED",        # 任务整体状态：等待执行
            request_payload=kafka_task_data,  # 保存原始请求数据（用于审计）
            dispatch_response=None,         # 下发响应（初始为空）
            dispatch_error=None,            # 下发错误（初始为空）
            created_by=created_by,          # 创建者ID
            case_count=len(case_ids),       # 包含的用例总数
            reported_case_count=0,          # 已上报进度的用例数（初始为0）
        )
        await task_doc.insert()  # 插入数据库

        # ========== 步骤6: 创建Kafka任务消息并发送到队列 ==========
        # 构建Kafka消息对象（符合消息管理器定义的格式）
        task_message = TaskMessage(
            task_id=task_id,                    # 任务ID
            task_type="execution_task",         # 任务类型标识
            task_data=kafka_task_data,          # 任务数据
            source="dmlv4-execution-api",       # 消息来源标识
            priority=1                          # 优先级（1-10，数字越大优先级越高）
        )

        # 使用Kafka消息管理器发送任务到队列
        # 默认主题：dmlv4.tasks（可在配置中修改）
        success = self.kafka_manager.send_task(task_message)

        # ========== 判断Kafka下发结果并更新任务状态 ==========
        if success:
            # 下发成功：更新任务状态为"已下发"
            task_doc.dispatch_status = "DISPATCHED"
            task_doc.dispatch_response = {
                "accepted": True,                                   # Kafka已接受消息
                "message": "Task dispatched to Kafka successfully", # 成功信息
                "kafka_topic": "dmlv4.tasks"                        # 实际发送的主题
            }
        else:
            # 下发失败：更新任务状态为"下发失败"，并抛出异常
            task_doc.dispatch_status = "DISPATCH_FAILED"
            task_doc.dispatch_error = "Failed to send task to Kafka"
            task_doc.dispatch_response = {
                "accepted": False,                                  # Kafka拒绝消息
                "message": "Failed to dispatch task to Kafka"       # 失败信息
            }
            await task_doc.save()  # 保存失败状态到数据库
            raise ValueError("Failed to dispatch task to Kafka")

        # ========== 步骤7: 为每个用例创建任务用例记录 ==========
        # 为什么要创建快照？因为用例可能在测试过程中被修改
        # 保存快照可以确保后续状态变更不影响历史记录的准确性
        for cid in case_ids:
            case_doc = doc_map[cid]  # 从映射中获取用例文档
            # 保存用例的关键信息快照（标题、版本、优先级等）
            snapshot = {
                "case_id": case_doc.case_id,     # 用例ID
                "title": case_doc.title,         # 用例标题
                "version": case_doc.version,     # 版本号
                "priority": case_doc.priority,   # 优先级
                "status": case_doc.status,       # 当前状态
            }
            # 创建任务用例文档，记录该用例在此任务中的执行状态
            await ExecutionTaskCaseDoc(
                task_id=task_id,          # 关联的任务ID
                case_id=cid,              # 用例ID
                case_snapshot=snapshot,   # 用例快照（JSON字段）
                status="QUEUED",          # 初始状态：等待执行
                last_seq=0,               # 最后处理的序列号（用于乱序保护）
            ).insert()

        # 保存任务文档的最终状态（包含下发成功的响应信息）
        await task_doc.save()

        # ========== 步骤8: 返回任务基本信息 ==========
        # 只返回前端需要的关键信息，避免返回过多内部细节
        return {
            "task_id": task_doc.task_id,           # 内部任务ID
            "external_task_id": task_doc.external_task_id,  # 外部任务ID
            "dispatch_status": task_doc.dispatch_status,    # 下发状态
            "overall_status": task_doc.overall_status,      # 整体状态
            "case_count": task_doc.case_count,              # 用例数量
            "created_at": task_doc.created_at,              # 创建时间
        }
