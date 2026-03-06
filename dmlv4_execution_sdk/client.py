"""SDK 核心客户端实现"""

import asyncio
import json
import logging
import threading
import time
from queue import Queue, Empty
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

import aiohttp

from .exceptions import (
    ReporterConfigError,
    ReporterValidationError,
    ReporterAuthError,
    ReporterDeliveryError,
    TaskNotFoundError,
    InvalidStatusError,
    NetworkError,
)
from .models import (
    ReporterConfig,
    TaskStats,
    ExecutionTask,
    TaskCase,
    CaseProgress,
    StepProgress,
    ProgressCallback,
    TaskStatus,
    CaseStatus,
    StepStatus,
    EventType,
)
from .utils import (
    generate_event_id,
    generate_timestamp,
    compute_signature,
    validate_status,
    ensure_event_time,
    safe_serialize,
    create_progress_headers,
    sanitize_error_message,
)


class ExecutionReporter:
    """同步版执行进度上报客户端"""

    def __init__(self, config: ReporterConfig):
        """初始化客户端

        Args:
            config: 客户端配置
        """
        if not config.base_url:
            raise ReporterConfigError("base_url is required")
        if not config.framework_id:
            raise ReporterConfigError("framework_id is required")
        if not config.secret:
            raise ReporterConfigError("secret is required")

        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._shutdown_event = threading.Event()
        self._queue = Queue(maxsize=config.queue_maxsize)
        self._worker_thread: Optional[threading.Thread] = None

        # 启动工作线程
        self._start_worker()

        # 设置日志
        self._logger = logging.getLogger(__name__)

    def _start_worker(self):
        """启动工作线程"""
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def _worker(self):
        """工作线程主循环"""
        while not self._shutdown_event.is_set():
            try:
                # 从队列获取任务
                callback_data = self._queue.get(timeout=1.0)
                self._process_callback(callback_data)
                self._queue.task_done()
            except Empty:
                continue
            except Exception as e:
                self._logger.error(f"Worker thread error: {e}")

    def _process_callback(self, callback_data: Dict[str, Any]):
        """处理单个回调请求"""
        try:
            # 这里应该是实际的HTTP请求逻辑
            # 为简化实现，我们假设有一个同步的HTTP客户端
            self._send_sync_request(callback_data)
        except Exception as e:
            self._logger.error(f"Failed to send callback: {e}")
            # TODO: 实现重试逻辑和落盘缓存

    def _send_sync_request(self, callback_data: Dict[str, Any]):
        """发送同步HTTP请求（简化实现）"""
        # 这里使用aiohttp的异步客户端，但在工作线程中运行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._send_request(callback_data))
        finally:
            loop.close()

    async def _send_request(self, callback_data: Dict[str, Any]):
        """发送HTTP请求"""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_sec)
            )

        try:
            # 计算签名
            timestamp = callback_data["timestamp"]
            event_id = callback_data["event_id"]
            raw_body = callback_data["raw_body"].encode("utf-8")
            signature = compute_signature(
                self.config.secret, str(timestamp), event_id, raw_body
            )

            # 创建请求头
            headers = create_progress_headers(
                self.config.framework_id, event_id, timestamp, signature
            )

            # 发送请求
            url = urljoin(self.config.base_url, "/api/v1/execution/callbacks/progress")
            async with self._session.post(url, headers=headers, data=raw_body) as response:
                if response.status >= 400:
                    error_msg = f"HTTP {response.status}: {await response.text()}"
                    raise ReporterDeliveryError(sanitize_error_message(error_msg))

        except aiohttp.ClientError as e:
            raise NetworkError(f"HTTP request failed: {e}")

    # === 任务管理 API ===

    def get_task(self, task_id: str) -> ExecutionTask:
        """获取任务详情"""
        # TODO: 实现获取任务详情的逻辑
        # 这里需要调用 /api/v1/execution/tasks/{task_id}
        raise NotImplementedError("Task retrieval not implemented yet")

    def list_tasks(
        self,
        framework: Optional[str] = None,
        overall_status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[ExecutionTask]:
        """查询任务列表"""
        # TODO: 实现任务列表查询逻辑
        # 这里需要调用 /api/v1/execution/tasks
        raise NotImplementedError("Task listing not implemented yet")

    def get_task_cases(
        self,
        task_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TaskCase]:
        """获取任务用例列表"""
        # TODO: 实现用例列表查询逻辑
        # 这里需要调用 /api/v1/execution/tasks/{task_id}/cases
        raise NotImplementedError("Task cases retrieval not implemented yet")

    # === 进度回传 API ===

    def report_task_status(
        self,
        task_id: str,
        external_task_id: Optional[str],
        status: str,
        seq: int,
        detail: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        event_time: Optional[datetime] = None
    ) -> None:
        """上报任务状态"""
        # 验证状态
        if not validate_status(status, [s.value for s in TaskStatus]):
            raise InvalidStatusError(f"Invalid task status: {status}")

        # 创建事件
        callback = ProgressCallback(
            task_id=task_id,
            external_task_id=external_task_id,
            event_type=EventType.TASK_STATUS.value,
            seq=seq,
            event_time=ensure_event_time(event_time),
            overall_status=status,
            summary=detail or {},
            meta={
                "sdk_name": "dmlv4-execution-sdk",
                "sdk_version": "0.1.0",
            }
        )

        self._queue_callback(callback, event_id)

    def report_case_status(
        self,
        task_id: str,
        case_id: str,
        status: str,
        seq: int,
        progress_percent: Optional[float] = None,
        step_total: Optional[int] = None,
        step_passed: Optional[int] = None,
        step_failed: Optional[int] = None,
        step_skipped: Optional[int] = None,
        event_id: Optional[str] = None,
        event_time: Optional[datetime] = None
    ) -> None:
        """上报用例状态"""
        # 验证状态
        if not validate_status(status, [s.value for s in CaseStatus]):
            raise InvalidStatusError(f"Invalid case status: {status}")

        # 创建用例进度
        case_progress = CaseProgress(
            case_id=case_id,
            status=status,
            progress_percent=progress_percent,
            step_total=step_total,
            step_passed=step_passed,
            step_failed=step_failed,
            step_skipped=step_skipped
        )

        # 创建事件
        callback = ProgressCallback(
            task_id=task_id,
            event_type=EventType.CASE_STATUS.value,
            seq=seq,
            event_time=ensure_event_time(event_time),
            case=case_progress,
            meta={
                "sdk_name": "dmlv4-execution-sdk",
                "sdk_version": "0.1.0",
            }
        )

        self._queue_callback(callback, event_id)

    def report_step_result(
        self,
        task_id: str,
        case_id: str,
        step_id: str,
        status: str,
        seq: int,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        message: Optional[str] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None,
        event_id: Optional[str] = None,
        event_time: Optional[datetime] = None
    ) -> None:
        """上报步骤结果"""
        # 验证状态
        if not validate_status(status, [s.value for s in StepStatus]):
            raise InvalidStatusError(f"Invalid step status: {status}")

        # 创建步骤进度
        step_progress = StepProgress(
            case_id=case_id,
            step_id=step_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            message=message,
            artifacts=artifacts or []
        )

        # 创建事件
        callback = ProgressCallback(
            task_id=task_id,
            event_type=EventType.STEP_RESULT.value,
            seq=seq,
            event_time=ensure_event_time(event_time),
            step=step_progress,
            meta={
                "sdk_name": "dmlv4-execution-sdk",
                "sdk_version": "0.1.0",
            }
        )

        self._queue_callback(callback, event_id)

    def heartbeat(self, task_id: str, seq: int, event_id: Optional[str] = None) -> None:
        """发送心跳"""
        callback = ProgressCallback(
            task_id=task_id,
            event_type=EventType.HEARTBEAT.value,
            seq=seq,
            event_time=ensure_event_time(),
            meta={
                "sdk_name": "dmlv4-execution-sdk",
                "sdk_version": "0.1.0",
            }
        )

        self._queue_callback(callback, event_id)

    def summary(
        self,
        task_id: str,
        overall_status: str,
        seq: int,
        totals: Dict[str, Any],
        event_id: Optional[str] = None
    ) -> None:
        """发送汇总信息"""
        callback = ProgressCallback(
            task_id=task_id,
            event_type=EventType.SUMMARY.value,
            seq=seq,
            event_time=ensure_event_time(),
            overall_status=overall_status,
            summary=totals,
            meta={
                "sdk_name": "dmlv4-execution-sdk",
                "sdk_version": "0.1.0",
            }
        )

        self._queue_callback(callback, event_id)

    def _queue_callback(self, callback: ProgressCallback, event_id: Optional[str] = None):
        """将回调请求加入队列"""
        if event_id is None:
            event_id = generate_event_id()

        # 序列化为JSON
        callback_dict = callback.to_dict()
        raw_body = safe_serialize(callback_dict)

        # 准备队列数据
        queue_data = {
            "callback": callback,
            "event_id": event_id,
            "timestamp": generate_timestamp(),
            "raw_body": raw_body,
            "callback_dict": callback_dict
        }

        try:
            self._queue.put_nowait(queue_data)
        except:
            raise ReporterDeliveryError("Queue is full, cannot enqueue callback")

    # === 便捷方法 ===

    def start_case(
        self,
        task_id: str,
        case_id: str,
        seq: int,
        event_id: Optional[str] = None
    ) -> None:
        """标记用例开始执行"""
        self.report_case_status(
            task_id=task_id,
            case_id=case_id,
            status=CaseStatus.RUNNING.value,
            seq=seq,
            event_id=event_id
        )

    def complete_case(
        self,
        task_id: str,
        case_id: str,
        status: str,
        seq: int,
        message: Optional[str] = None,
        event_id: Optional[str] = None
    ) -> None:
        """标记用例执行完成"""
        # 如果状态是PASSED/FAILED等结束状态，可以记录到summary中
        self.report_case_status(
            task_id=task_id,
            case_id=case_id,
            status=status,
            seq=seq,
            event_id=event_id
        )

    def update_case_progress(
        self,
        task_id: str,
        case_id: str,
        progress_percent: float,
        seq: int,
        event_id: Optional[str] = None
    ) -> None:
        """更新用例进度百分比"""
        self.report_case_status(
            task_id=task_id,
            case_id=case_id,
            status=CaseStatus.RUNNING.value,  # 运行时更新进度
            seq=seq,
            progress_percent=progress_percent,
            event_id=event_id
        )

    # === 生命周期管理 ===

    def flush(self, timeout_sec: Optional[float] = None) -> None:
        """等待所有待处理请求完成"""
        timeout = timeout_sec or self.config.timeout_sec * 2
        self._queue.join()  # 等待所有任务完成

    def close(self) -> None:
        """关闭客户端"""
        # 设置关闭标志
        self._shutdown_event.set()

        # 等待工作线程结束
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)

        # 关闭HTTP会话
        if self._session:
            asyncio.run(self._session.close())


class AsyncExecutionReporter:
    """异步版执行进度上报客户端"""

    def __init__(self, config: ReporterConfig):
        """初始化异步客户端

        Args:
            config: 客户端配置
        """
        if not config.base_url:
            raise ReporterConfigError("base_url is required")
        if not config.framework_id:
            raise ReporterConfigError("framework_id is required")
        if not config.secret:
            raise ReporterConfigError("secret is required")

        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._logger = logging.getLogger(__name__ + ".async")

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建HTTP会话"""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_sec)
            )
        return self._session

    async def _send_request(self, callback_dict: Dict[str, Any], event_id: str, timestamp: int) -> None:
        """发送异步HTTP请求"""
        session = await self._get_session()

        # 计算签名
        raw_body = safe_serialize(callback_dict).encode("utf-8")
        signature = compute_signature(
            self.config.secret, str(timestamp), event_id, raw_body
        )

        # 创建请求头
        headers = create_progress_headers(
            self.config.framework_id, event_id, timestamp, signature
        )

        # 发送请求
        url = urljoin(self.config.base_url, "/api/v1/execution/callbacks/progress")
        async with session.post(url, headers=headers, data=raw_body) as response:
            if response.status >= 400:
                error_msg = f"HTTP {response.status}: {await response.text()}"
                raise ReporterDeliveryError(sanitize_error_message(error_msg))

    # 实现与同步版本相同的API，但使用async/await
    # 这里为节省篇幅，只实现核心方法

    async def report_task_status(
        self,
        task_id: str,
        external_task_id: Optional[str],
        status: str,
        seq: int,
        detail: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        event_time: Optional[datetime] = None
    ) -> None:
        """上报任务状态"""
        if not validate_status(status, [s.value for s in TaskStatus]):
            raise InvalidStatusError(f"Invalid task status: {status}")

        callback = ProgressCallback(
            task_id=task_id,
            external_task_id=external_task_id,
            event_type=EventType.TASK_STATUS.value,
            seq=seq,
            event_time=ensure_event_time(event_time),
            overall_status=status,
            summary=detail or {},
            meta={
                "sdk_name": "dmlv4-execution-sdk",
                "sdk_version": "0.1.0",
            }
        )

        if event_id is None:
            event_id = generate_event_id()

        callback_dict = callback.to_dict()
        timestamp = generate_timestamp()

        await self._send_request(callback_dict, event_id, timestamp)

    async def close(self) -> None:
        """关闭异步客户端"""
        if self._session:
            await self._session.close()