"""
执行调度器运行器：将 scheduler 循环从 InfrastructureRegistry 中拆分出来。

管理 asyncio 后台任务的启动/停止生命周期。
"""

from __future__ import annotations

import asyncio
import logging

from app.shared.core.logger import log as logger

logger = logging.getLogger(__name__)


class ExecutionSchedulerRunner:
    """后台调度循环，定期下发到期的执行任务。"""

    def __init__(
        self,
        interval_sec: int = 30,
    ) -> None:
        self._task: asyncio.Task | None = None
        self._interval = max(interval_sec, 1)

    async def start(self) -> None:
        """启动后台调度循环（幂等）。"""
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """停止后台调度循环（幂等）。"""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _loop(self) -> None:
        """调度主循环。"""
        while True:
            try:
                logger.info("执行调度循环触发")
                await self._dispatch_due()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("执行调度循环异常: %s", exc)
            await asyncio.sleep(self._interval)

    async def _dispatch_due(self) -> None:
        """实际调度逻辑，子类或外部可覆盖。"""
        try:
            from app.modules.execution.service.task_scheduler import ExecutionTaskScheduler

            scheduler = ExecutionTaskScheduler()
            await scheduler.dispatch_due_tasks()
        except ImportError:
            logger.warning("ExecutionTaskScheduler 不可用，跳过调度")
