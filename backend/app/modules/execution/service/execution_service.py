"""
测试执行服务模块。

该模块负责与外部测试框架集成，处理测试任务的创建、分发、进度跟踪和结果回调。
主要功能包括：
1. 接收来自前端的任务创建请求，验证用例并生成任务
2. 将任务消息发送到Kafka队列，供外部测试框架消费
3. 处理外部测试框架的进度回调和执行结果
4. 提供任务状态查询和用例进度查询功能

主要数据模型：
- ExecutionTaskDoc: 任务文档，记录任务的基本信息和状态
- ExecutionTaskCaseDoc: 任务用例文档，记录每个用例的执行进度
- ExecutionEventDoc: 事件文档，记录所有回调事件的审计日志
"""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo.errors import DuplicateKeyError

# 导入核心依赖：
# - 测试用例文档：用于验证用例存在性
# - 配置对象：用于获取JWT密钥等配置
# - Kafka消息管理器：用于与外部测试框架通信
# - 基础服务类：提供服务基类功能

from app.modules.execution.repository.models import (
    ExecutionEventDoc,
    ExecutionTaskCaseDoc,
    ExecutionTaskDoc,
)
from app.modules.test_specs.repository.models import TestCaseDoc
from app.shared.db.config import settings
from app.shared.kafka import KafkaMessageManager, TaskMessage, ResultMessage
from app.shared.service import BaseService, SequenceIdService


class ExecutionService(BaseService):
    """
    执行任务编排与回调处理服务。

    该服务作为DMLv4系统与外部测试框架之间的桥梁，主要职责包括：
    1. 接收并验证任务创建请求
    2. 将任务分发到Kafka队列供外部测试框架消费
    3. 处理来自外部测试框架的进度回调和执行结果
    4. 提供任务和用例状态的查询接口
    5. 管理任务全生命周期状态跟踪

    服务支持异步上下文管理，确保Kafka连接的正确初始化和清理。
    """

    # 允许的任务状态枚举
    # 用于验证从外部测试框架返回的任务状态值
    _ALLOWED_TASK_STATUS = {
        "QUEUED",        # 任务已创建，等待执行
        "RUNNING",       # 任务正在执行中
        "PASSED",        # 任务执行成功完成
        "FAILED",        # 任务执行失败
        "PARTIAL_FAILED", # 任务部分用例失败
        "CANCELLED",     # 任务被取消
        "TIMEOUT",       # 任务执行超时
    }

    # 允许的用例状态枚举
    # 用于验证从外部测试框架返回的用例状态值
    _ALLOWED_CASE_STATUS = {
        "QUEUED",        # 用例已加入任务，等待执行
        "RUNNING",       # 用例正在执行中
        "PASSED",        # 用例执行成功
        "FAILED",        # 用例执行失败
        "SKIPPED",       # 用例被跳过
        "BLOCKED",       # 用例被阻塞
        "ERROR",         # 用例执行出现错误
    }

    def __init__(self):
        """初始化执行服务。

        创建Kafka消息管理器实例并启动连接。Kafka用于与外部测试框架进行异步消息传递。
        """
        super().__init__()
        # 创建Kafka消息管理器实例，用于发送任务到外部测试框架和接收执行结果
        self.kafka_manager = KafkaMessageManager()
        # 启动Kafka连接（同步方式，确保在异步上下文外也能正常工作）
        self.kafka_manager.start()

    async def __aenter__(self):
        """异步上下文入口。

        Returns:
            self: 返回服务实例本身

        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文退出。

        确保在服务结束时正确关闭Kafka连接，释放资源。

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪信息

        """
        if self.kafka_manager:
            self.kafka_manager.stop()

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

    def handle_execution_result(self, task_msg: TaskMessage) -> ResultMessage:
        """
        处理外部测试框架返回的执行结果。

        这是Kafka消息处理器回调函数，用于处理来自外部测试框架的执行结果消息。
        该方法以非阻塞方式异步更新数据库，避免阻塞消息处理流程。

        处理的执行结果包括：
        1. 任务整体状态的更新（开始时间、结束时间、最终状态）
        2. 各个用例的执行状态更新

        注意：此方法不会抛出异常，而是通过返回ResultMessage来表示处理结果。
        如果处理失败，错误信息会记录在ResultMessage中。

        Args:
            task_msg: Kafka任务消息，包含：
                - task_id: 任务ID
                - task_data: 执行结果数据，包括result字段
                    - result.overall_status: 任务整体状态
                    - result.started_at: 任务开始时间
                    - result.finished_at: 任务结束时间
                    - result.case_results: 各用例执行结果列表
                        - case_results[].case_id: 用例ID
                        - case_results[].status: 用例状态
                        - case_results[].progress_percent: 执行进度百分比
                        - case_results[].finished_at: 用例结束时间

        Returns:
            ResultMessage: 包含处理结果的消息对象：
                - status: "SUCCESS" 或 "FAILED"
                - task_id: 任务ID
                - result_data: 成功时包含{"updated": True}
                - error_message: 失败时的错误信息
                - executor: 执行器标识
        """
        try:
            # ========== 解析Kafka消息数据 ==========
            # 从消息对象中提取任务数据
            result_data = task_msg.task_data

            # 提取任务ID和执行结果对象
            task_id = result_data.get("task_id")
            execution_result = result_data.get("result", {})  # 默认为空对象，避免KeyError

            # ========== 异步处理数据库更新 ==========
            # 为什么使用create_task？
            # - Kafka消息处理需要快速响应，不能被数据库更新阻塞
            # - 使用create_task在后台异步执行数据库操作
            # - 即使更新失败，也不影响Kafka消息的确认
            import asyncio

            async def update_task():
                """后台异步更新任务和用例状态。

                此函数在事件循环中并发执行，不会阻塞主流程。
                """
                # 查询任务文档（不存在则跳过更新）
                task_doc = await ExecutionTaskDoc.find_one(
                    ExecutionTaskDoc.task_id == task_id
                )
                if task_doc:
                    # ========== 更新任务整体状态 ==========
                    # 只更新非空字段，避免覆盖已有数据
                    overall_status = execution_result.get("overall_status")
                    if overall_status:  # 例如：PASSED, FAILED, RUNNING等
                        task_doc.overall_status = overall_status

                    started_at = execution_result.get("started_at")
                    if started_at:  # 任务开始时间（首次收到RUNNING时设置）
                        task_doc.started_at = started_at

                    finished_at = execution_result.get("finished_at")
                    if finished_at:  # 任务结束时间（进入终态时设置）
                        task_doc.finished_at = finished_at

                    await task_doc.save()

                    # ========== 批量更新用例状态 ==========
                    # 遍历所有用例的执行结果，逐个更新数据库
                    case_results = execution_result.get("case_results", [])
                    for case_result in case_results:
                        case_id = case_result.get("case_id")
                        # 查询对应的任务用例文档
                        case_doc = await ExecutionTaskCaseDoc.find_one(
                            ExecutionTaskCaseDoc.task_id == task_id,
                            ExecutionTaskCaseDoc.case_id == case_id
                        )
                        if case_doc:  # 存在才更新，避免异常
                            # 更新用例状态（默认为UNKNOWN）
                            case_doc.status = case_result.get("status", "UNKNOWN")
                            # 更新执行进度百分比（0-100之间的浮点数）
                            case_doc.progress_percent = case_result.get("progress_percent")
                            # 更新用例结束时间
                            case_doc.finished_at = case_result.get("finished_at")
                            await case_doc.save()

            # 在后台调度异步任务（立即返回，不等待完成）
            # 这样Kafka消费者可以快速确认消息，继续处理下一条
            asyncio.create_task(update_task())

            # ========== 返回成功响应 ==========
            # 告诉Kafka消息管理器：此消息已成功接收并处理
            return ResultMessage(
                task_id=task_id,                              # 任务ID
                status="SUCCESS",                             # 处理状态：成功
                result_data={"updated": True},                # 结果数据：已更新
                executor="execution-service"                  # 执行器标识
            )

        except Exception as e:
            # ========== 异常处理（不抛出） ==========
            # 为什么捕获异常但不抛出？
            # - Kafka消息处理需要快速确认，避免消息重复投递
            # - 异常会记录在返回的ResultMessage中，供监控和调试
            # - 业务逻辑错误不应该影响消息队列的正常运行
            return ResultMessage(
                task_id=task_msg.task_id,                     # 任务ID
                status="FAILED",                              # 处理状态：失败
                error_message=str(e),                         # 错误信息（便于调试）
                executor="execution-service"                  # 执行器标识
            )

    async def setup_kafka_result_handler(self):
        """
        设置Kafka结果处理器。

        将handle_execution_result方法注册为execution_result事件的处理器。
        当Kafka收到execution_result类型的消息时，会回调此方法处理执行结果。
        """
        self.kafka_manager.register_task_handler("execution_result", self.handle_execution_result)

    async def start_kafka_listener(self):
        """
        启动Kafka消息监听器。

        执行以下操作：
        1. 注册execution_result事件处理器
        2. 启动后台任务持续监听和处理Kafka消息

        注意：此方法会启动一个长期运行的后台任务，应该在服务启动时调用。
        """
        # 注册结果处理器
        await self.setup_kafka_result_handler()
        # 在后台持续处理Kafka消息（消费队列中的消息）
        import asyncio
        asyncio.create_task(self.kafka_manager.process_tasks())

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        获取指定任务的详细信息，包括用例统计。

        Args:
            task_id: 任务ID

        Returns:
            包含任务完整信息的字典：
                - 任务的所有字段（从文档转换而来）
                - stats: 用例执行统计信息，包含以下键：
                    - queued: 等待执行的用例数
                    - running: 正在执行的用例数
                    - passed: 执行通过的用例数
                    - failed: 执行失败的用例数
                    - skipped: 被跳过的用例数
                    - blocked: 被阻塞的用例数
                    - error: 出现错误的用例数

        Raises:
            KeyError: 当任务不存在或已被软删除时
        """
        # ========== 查询任务文档 ==========
        # 使用find_one查询单个文档，同时过滤已软删除的任务
        # 注意：这里没有使用await task.to_list()，因为find_one直接返回文档对象或None
        task = await ExecutionTaskDoc.find_one(
            ExecutionTaskDoc.task_id == task_id,
            {"is_deleted": False},  # 过滤条件：未软删除
        )
        if not task:
            raise KeyError("task not found")

        # ========== 计算用例执行统计信息 ==========
        # 实时统计各状态用例的数量，返回给前端展示任务概况
        stats = await self._compute_task_stats(task_id)

        # ========== 转换为API响应格式 ==========
        # 将文档对象转换为字典（BaseService提供的工具方法）
        data = self._doc_to_dict(task)
        # 添加用例统计信息（前端用于显示进度条和状态分布）
        data["stats"] = stats
        return data

    async def list_tasks(
        self,
        created_by: Optional[str] = None,
        framework: Optional[str] = None,
        overall_status: Optional[str] = None,
        dispatch_status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        查询任务列表，支持多种过滤条件。

        Args:
            created_by: 按创建者过滤（可选）
            framework: 按测试框架类型过滤（可选）
            overall_status: 按任务整体状态过滤（可选）
            dispatch_status: 按任务下发状态过滤（可选）
            limit: 返回记录数量限制，默认20
            offset: 偏移量（用于分页），默认0

        Returns:
            任务列表，每个元素包含任务的字典表示（按创建时间降序排列）

        Note:
            - 多个过滤条件之间是AND关系
            - 结果按创建时间降序排列（最新的在前）
            - 始终过滤掉已软删除的任务
        """
        # ========== 构建基础查询条件 ==========
        # 始终过滤掉已软删除的任务（软删除模式：is_deleted=True）
        query = ExecutionTaskDoc.find({"is_deleted": False})

        # ========== 应用可选的过滤条件 ==========
        # 支持链式调用，Beanie ODM会优化为单次查询
        if created_by:
            # 按创建者过滤（例如：查看自己创建的任务）
            query = query.find(ExecutionTaskDoc.created_by == created_by)
        if framework:
            # 按测试框架过滤（例如：只查看pytest框架的任务）
            query = query.find(ExecutionTaskDoc.framework == framework)
        if overall_status:
            # 按任务状态过滤（例如：只查看运行中的任务）
            query = query.find(ExecutionTaskDoc.overall_status == overall_status)
        if dispatch_status:
            # 按下发状态过滤（例如：查看下发失败的任务）
            query = query.find(ExecutionTaskDoc.dispatch_status == dispatch_status)

        # ========== 执行查询并返回结果 ==========
        # 排序：按创建时间降序（最新的任务在前）
        # 分页：跳过offset条记录，返回limit条记录
        docs = await query.sort("-created_at").skip(offset).limit(limit).to_list()
        # 转换为字典列表（过滤掉MongoDB内部字段）
        return [self._doc_to_dict(doc) for doc in docs]

    async def list_task_cases(
        self,
        task_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        查询指定任务下的用例列表，支持按状态过滤。

        Args:
            task_id: 任务ID
            status: 按用例状态过滤（可选）
            limit: 返回记录数量限制，默认50
            offset: 偏移量（用于分页），默认0

        Returns:
            用例列表，每个元素包含用例的字典表示（按创建时间升序排列）

        Raises:
            KeyError: 当任务不存在或已被软删除时

        Note:
            - 首先验证任务存在性
            - 支持按用例状态过滤
            - 结果按创建时间升序排列（最早创建的在前）
        """
        # ========== 验证任务存在性 ==========
        # 首先要确保任务存在且未被软删除，否则查询用例没有意义
        # 注意：这里使用find_one而不是find，因为只需要判断存在性
        task = await ExecutionTaskDoc.find_one(
            ExecutionTaskDoc.task_id == task_id,
            {"is_deleted": False},  # 过滤条件：未软删除
        )
        if not task:
            raise KeyError("task not found")

        # ========== 构建用例查询条件 ==========
        # 查询条件：task_id匹配当前任务
        query = ExecutionTaskCaseDoc.find(ExecutionTaskCaseDoc.task_id == task_id)
        if status:
            # 可选过滤：按用例状态过滤（例如：只看运行中的用例）
            query = query.find(ExecutionTaskCaseDoc.status == status)

        # ========== 执行查询并返回结果 ==========
        # 排序：按创建时间升序（最早创建的用例在前，便于追踪执行顺序）
        # 分页：跳过offset条记录，返回limit条记录
        docs = await query.sort("created_at").skip(offset).limit(limit).to_list()
        # 转换为字典列表（过滤掉MongoDB内部字段）
        return [self._doc_to_dict(doc) for doc in docs]

    async def handle_progress_callback(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        处理外部测试框架的进度回调。

        这是处理来自外部测试框架HTTP回调的入口方法。
        主要职责：
        1. 验证回调请求的安全签名
        2. 验证任务的存在性和有效性
        3. 记录回调事件到审计日志
        4. 防重复处理（通过event_id去重）
        5. 应用进度更新到任务和用例
        6. 记录处理结果和错误

        安全验证机制：
        - 使用HMAC-SHA256签名验证请求真实性
        - 验证请求时间戳（5分钟窗口期），防止重放攻击
        - 通过event_id去重，避免重复处理同一事件

        Args:
            headers: HTTP请求头，必须包含：
                - x-framework-id: 测试框架标识
                - x-event-id: 事件唯一ID（用于去重）
                - x-timestamp: 事件时间戳
                - x-signature: HMAC-SHA256签名
            raw_body: 原始请求体（字节串，用于签名验证）
            payload: 解析后的JSON负载，包含：
                - task_id: 任务ID
                - event_type: 事件类型
                - seq: 事件序列号（用于乱序保护）
                - event_time: 事件发生时间
                - overall_status: 任务整体状态（可选）
                - case: 单个用例进度（可选）
                    - case.case_id: 用例ID
                    - case.status: 用例状态
                    - case.progress_percent: 执行进度
                    - case.step_total/step_passed/step_failed/step_skipped: 步骤统计

        Returns:
            包含处理结果的字典：
                - accepted: 是否接受回调（true表示验证通过）
                - deduplicated: 是否为重复事件（true表示已处理过）

        Raises:
            PermissionError: 当签名验证失败、缺少必需头、或时间戳超时时
            ValueError: 当缺少task_id或状态值无效时
            KeyError: 当任务不存在时
        """
        # ========== 步骤1: 从请求头提取签名验证所需的信息 ==========
        # 外部测试框架必须在请求头中提供以下信息：
        framework_id = headers.get("x-framework-id")    # 测试框架标识（区分不同的测试框架）
        event_id = headers.get("x-event-id")           # 事件唯一ID（用于幂等性保证）
        timestamp = headers.get("x-timestamp")         # 事件时间戳（用于防重放攻击）
        signature = headers.get("x-signature")         # HMAC-SHA256签名（验证请求真实性）

        # 验证所有必需的签名头都存在，缺失则拒绝请求
        if not framework_id or not event_id or not timestamp or not signature:
            raise PermissionError("missing signature headers")

        # ========== 步骤2: 验证请求签名的有效性 ==========
        # 使用HMAC-SHA256算法验证请求体完整性和来源可信性
        # 这确保请求确实来自授权的测试框架，且数据未被篡改
        self._verify_signature(
            secret=settings.JWT_SECRET_KEY,  # 使用JWT密钥作为签名密钥
            timestamp=timestamp,              # 时间戳
            event_id=event_id,               # 事件ID
            raw_body=raw_body,               # 原始请求体（字节串）
            signature=signature,             # 请求提供的签名
        )

        # ========== 步骤3: 提取并验证任务ID ==========
        # 任务ID是必需的，用于关联到具体的测试任务
        task_id = payload.get("task_id")
        if not task_id:
            raise ValueError("task_id is required")

        # ========== 步骤4: 验证任务存在且未被软删除 ==========
        # 确保回调对应的任务确实存在，且未被标记为删除
        task_doc = await ExecutionTaskDoc.find_one(
            ExecutionTaskDoc.task_id == task_id,
            {"is_deleted": False},  # 只查询未软删除的任务
        )
        if not task_doc:
            raise KeyError("task not found")

        # ========== 步骤5: 记录回调事件到审计日志 ==========
        # 所有回调事件都会被记录，用于调试和问题追踪
        # 即使处理失败，事件也会被记录（便于分析失败原因）
        event_doc = ExecutionEventDoc(
            task_id=task_id,                                    # 关联的任务ID
            event_id=event_id,                                  # 事件唯一ID
            event_type=str(payload.get("event_type") or "UNKNOWN"),  # 事件类型
            seq=int(payload.get("seq") or 0),                   # 事件序列号（乱序保护）
            source_time=payload.get("event_time"),              # 事件发生时间（源时间）
            raw_payload=payload,                                # 原始负载（完整JSON）
            processed=False,                                    # 是否处理成功（初始为False）
        )

        # ========== 步骤6: 尝试插入事件文档（利用唯一索引去重） ==========
        # 事件文档在数据库中设置了event_id的唯一索引
        # 如果event_id已存在，MongoDB会抛出DuplicateKeyError
        try:
            await event_doc.insert()
        except DuplicateKeyError:
            # 事件已存在，说明是重复回调（可能是网络重试导致）
            # 直接返回成功，保证幂等性（同样的事件处理多次，结果一致）
            return {"accepted": True, "deduplicated": True}

        # ========== 步骤7: 应用进度更新到任务和用例 ==========
        try:
            # 调用内部方法应用进度更新
            await self._apply_progress(task_doc, payload, event_id)
            # ========== 更新成功 ==========
            # 标记事件为已处理，并清除错误信息
            event_doc.processed = True
            event_doc.process_error = None
            await event_doc.save()
        except Exception as exc:
            # ========== 更新失败 ==========
            # 标记事件为处理失败，记录错误信息
            event_doc.processed = False
            event_doc.process_error = str(exc)  # 记录具体错误信息，便于调试
            await event_doc.save()
            # 重新抛出异常，让上层HTTP处理器返回错误响应
            raise

        # ========== 返回成功响应 ==========
        # accepted: 签名验证通过，回调被接受
        # deduplicated: 不是重复事件是新事件
        return {"accepted": True, "deduplicated": False}

    async def _apply_progress(self, task_doc: ExecutionTaskDoc, payload: Dict[str, Any], event_id: str) -> None:
        """
        应用进度更新到任务和用例文档。

        这是内部方法，负责根据回调负载更新任务和用例的状态。
        支持乱序保护机制，确保即使回调消息乱序到达也能正确处理。

        Args:
            task_doc: 任务文档对象
            payload: 回调负载数据
            event_id: 事件ID（用于记录最后处理的事件）

        Raises:
            ValueError: 当状态值不在允许的枚举范围内时
            KeyError: 当用例不存在时
        """
        now = datetime.now(timezone.utc)  # 获取当前UTC时间（避免时区问题）

        # ========== 记录最后回调时间 ==========
        # 用于监控任务活跃度和检测长时间无响应的任务
        task_doc.last_callback_at = now

        # ========== 步骤1: 更新任务整体状态 ==========
        incoming_overall = payload.get("overall_status")
        if incoming_overall:
            # 标准化状态值为大写（统一格式）
            # 例如：将"passed"、"PASSED"都转换为"PASSED"
            incoming_overall = str(incoming_overall).upper()
            # 验证状态值是否在允许的枚举范围内（防止脏数据）
            if incoming_overall not in self._ALLOWED_TASK_STATUS:
                raise ValueError("invalid overall_status")

            # 更新任务状态
            task_doc.overall_status = incoming_overall

            # ========== 特殊情况：记录任务开始时间 ==========
            # 只有当状态首次变为RUNNING且之前未记录开始时间时，才设置started_at
            # 这样可以准确记录任务的实际开始时间，而不是回调时间
            if incoming_overall == "RUNNING" and task_doc.started_at is None:
                task_doc.started_at = now

            # ========== 特殊情况：记录任务结束时间 ==========
            # 当任务进入终态（完成/失败/部分失败/取消/超时）时，记录结束时间
            # 这些状态表示任务不再执行，可以计算总耗时
            if incoming_overall in {"PASSED", "FAILED", "PARTIAL_FAILED", "CANCELLED", "TIMEOUT"}:
                task_doc.finished_at = now

        # ========== 步骤2: 更新单个用例的进度 ==========
        # 注意：一个回调可能只包含任务整体进度，也可能包含单个用例的进度
        case_payload = payload.get("case") or {}  # 获取用例进度（可能为空）
        case_id = case_payload.get("case_id")    # 用例ID（字符串）
        # 事件序列号，用于乱序保护（递增的数字，确保只处理最新事件）
        seq = int(payload.get("seq") or 0)

        # 只有当回调中包含用例信息时，才更新用例状态
        if case_id:
            # 查询对应的任务用例文档
            case_doc = await ExecutionTaskCaseDoc.find_one(
                ExecutionTaskCaseDoc.task_id == task_doc.task_id,       # 任务ID匹配
                ExecutionTaskCaseDoc.case_id == str(case_id),           # 用例ID匹配
            )
            if not case_doc:
                raise KeyError("task case not found")

            # ========== 乱序保护机制 ==========
            # 问题：网络延迟可能导致回调乱序到达（例如：seq=5的回调比seq=3的晚到）
            # 解决：只处理序列号更大的事件，忽略旧事件
            # 如果当前事件的序列号小于等于已处理的序列号，则跳过处理
            if seq <= case_doc.last_seq:
                # 旧事件：虽然跳过了用例更新，但仍需更新任务的最后回调时间
                await task_doc.save()
                return

            # ========== 更新用例状态 ==========
            incoming_case_status = case_payload.get("status")
            if incoming_case_status:
                # 标准化状态值为大写（统一格式）
                incoming_case_status = str(incoming_case_status).upper()
                # 验证状态值是否在允许的枚举范围内（防止脏数据）
                if incoming_case_status not in self._ALLOWED_CASE_STATUS:
                    raise ValueError("invalid case status")

                # 更新用例状态
                case_doc.status = incoming_case_status

                # ========== 特殊情况：记录用例开始时间 ==========
                # 只有当状态首次变为RUNNING且之前未记录开始时间时，才设置started_at
                if incoming_case_status == "RUNNING" and case_doc.started_at is None:
                    case_doc.started_at = now

                # ========== 特殊情况：记录用例结束时间 ==========
                # 当用例进入终态时，记录结束时间（可用于计算用例耗时）
                if incoming_case_status in {"PASSED", "FAILED", "SKIPPED", "BLOCKED", "ERROR"}:
                    case_doc.finished_at = now

            # ========== 更新用例的执行统计信息（可选字段） ==========
            # 这些字段可能不存在于某些测试框架的回调中，所以使用条件更新

            # 执行进度百分比（0-100之间的浮点数，例如：45.5表示45.5%）
            if case_payload.get("progress_percent") is not None:
                case_doc.progress_percent = float(case_payload.get("progress_percent"))
            # 步骤总数（整个用例包含的测试步骤数）
            if case_payload.get("step_total") is not None:
                case_doc.step_total = int(case_payload.get("step_total"))
            # 通过的步骤数（执行成功的步骤数）
            if case_payload.get("step_passed") is not None:
                case_doc.step_passed = int(case_payload.get("step_passed"))
            # 失败的步骤数（执行失败的步骤数）
            if case_payload.get("step_failed") is not None:
                case_doc.step_failed = int(case_payload.get("step_failed"))
            # 跳过的步骤数（被跳过的步骤数）
            if case_payload.get("step_skipped") is not None:
                case_doc.step_skipped = int(case_payload.get("step_skipped"))

            # ========== 更新序列号和最后处理的事件ID ==========
            case_doc.last_seq = seq               # 更新最后处理的序列号
            case_doc.last_event_id = event_id     # 记录最后处理的事件ID（用于调试）
            # 保存用例文档的更改到数据库
            await case_doc.save()

        # ========== 步骤3: 更新任务统计信息 ==========
        # 统计已上报进度的用例数量（即last_seq > 0的用例）
        # 注意：last_seq > 0表示该用例至少收到过一次进度回调
        # 这个统计用于追踪任务的整体进度和活跃度
        reported_count = await ExecutionTaskCaseDoc.find(
            ExecutionTaskCaseDoc.task_id == task_doc.task_id,
            {"last_seq": {"$gt": 0}},  # 查询条件：序列号大于0（即已上报进度）
        ).count()  # 直接返回计数，不需要获取文档列表
        task_doc.reported_case_count = reported_count
        # 保存任务文档的更改（包括最后回调时间和上报用例数）
        await task_doc.save()

    async def _compute_task_stats(self, task_id: str) -> Dict[str, int]:
        """
        计算任务的用例执行统计信息。

        统计指定任务下各状态用例的数量，用于前端展示任务概况。
        该方法实时查询数据库，确保统计数据的准确性。

        Args:
            task_id: 任务ID

        Returns:
            包含各种状态用例数量的字典：
                - queued: 等待执行的用例数
                - running: 正在执行的用例数
                - passed: 执行通过的用例数
                - failed: 执行失败的用例数
                - skipped: 被跳过的用例数
                - blocked: 被阻塞的用例数
                - error: 出现错误的用例数

        Note:
            - 状态名称统一转换为小写作为字典的键
            - 如果用例状态不在预定义的枚举中，会被忽略（不会导致错误）
        """
        # ========== 查询任务下所有用例 ==========
        # 获取指定任务的所有用例文档（包含所有状态）
        docs = await ExecutionTaskCaseDoc.find(ExecutionTaskCaseDoc.task_id == task_id).to_list()

        # ========== 初始化统计结果 ==========
        # 所有计数从0开始，后续遍历时递增
        # 注意：状态名统一使用小写（避免大小写不一致问题）
        stats = {
            "queued": 0,    # 等待执行
            "running": 0,   # 正在执行
            "passed": 0,    # 执行通过
            "failed": 0,    # 执行失败
            "skipped": 0,   # 被跳过
            "blocked": 0,   # 被阻塞
            "error": 0,     # 出现错误
        }

        # ========== 遍历所有用例，统计各状态的数量 ==========
        for doc in docs:
            # 获取用例状态并转换为小写（统一格式）
            # 例如：将"Queued"、"QUEUED"、"passed"都转换为"queued"
            key = (doc.status or "").lower()  # 如果status为None则使用空字符串
            # 只有当状态在预定义的枚举中时，才增加计数
            # 如果遇到未知状态（例如"UNKNOWN"），则忽略（不会导致错误）
            if key in stats:
                stats[key] += 1

        return stats  # 返回统计结果字典

    @staticmethod
    def _verify_signature(
        secret: str,          # 签名密钥（JWT_SECRET_KEY）
        timestamp: str,       # 事件时间戳（字符串形式）
        event_id: str,        # 事件唯一ID
        raw_body: bytes,      # 原始请求体（字节串）
        signature: str,       # 请求提供的签名
    ) -> None:
        try:
            # ========== 步骤1: 验证时间戳 ==========
            # 将时间戳字符串转换为整数
            ts = int(timestamp)
        except ValueError as exc:
            # 时间戳格式错误（非数字字符串）
            raise PermissionError("invalid timestamp") from exc

        # ========== 步骤2: 验证时间戳有效性（防重放攻击） ==========
        # 计算当前时间与事件时间的差值
        now = int(time.time())
        # 允许的时间窗口：300秒（5分钟）
        # 如果事件时间超过5分钟，则认为可能是重放攻击，拒绝请求
        if abs(now - ts) > 300:
            raise PermissionError("timestamp out of window")

        # ========== 步骤3: 计算预期签名 ==========
        # 签名格式：timestamp\n{event_id}\n{raw_body}
        # \n是换行符，确保每个部分独立，避免拼接攻击
        signing = f"{timestamp}\\n{event_id}\\n".encode("utf-8") + raw_body
        # 使用HMAC-SHA256算法计算签名
        expected = hmac.new(secret.encode("utf-8"), signing, hashlib.sha256).hexdigest()

        # ========== 步骤4: 比较签名 ==========
        # 使用compare_digest而不是直接比较，避免时序攻击
        # compare_digest的执行时间与输入无关，防止通过响应时间猜测签名
        if not hmac.compare_digest(expected, signature):
            # 签名不匹配：可能是请求被篡改或密钥错误
            raise PermissionError("invalid signature")