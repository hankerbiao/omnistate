"""执行模块命令定义 - Phase 5

显式的命令对象用于定义执行任务分发的高风险操作。
通过发件箱模式确保可靠的外部事件发布。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class DispatchExecutionTaskCommand:
    """分发执行任务命令

    这个命令表示要分发一个测试任务到外部测试框架。
    通过发件箱模式确保任务能够可靠地发布到Kafka队列。
    """
    # 任务基本信息
    task_id: str
    external_task_id: str
    framework: str
    trigger_source: str
    created_by: str

    # 测试用例信息
    case_ids: List[str]

    # 任务配置
    callback_url: Optional[str] = None
    dut: Optional[Dict[str, Any]] = None
    runtime_config: Optional[Dict[str, Any]] = None

    # Kafka任务数据（内部生成）
    kafka_task_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.kafka_task_data is None:
            self.kafka_task_data = self._build_kafka_task_data()

    def _build_kafka_task_data(self) -> Dict[str, Any]:
        """构建Kafka任务数据"""
        return {
            "task_id": self.task_id,
            "external_task_id": self.external_task_id,
            "framework": self.framework,
            "trigger_source": self.trigger_source,
            "callback_url": self.callback_url,
            "dut": self.dut or {},
            "cases": [{"case_id": cid} for cid in self.case_ids],
            "runtime_config": self.runtime_config or {},
            "created_by": self.created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def validate(self) -> List[str]:
        """验证命令的有效性

        Returns:
            验证错误列表，如果为空则表示验证通过
        """
        errors = []

        if not self.task_id:
            errors.append("task_id is required")

        if not self.external_task_id:
            errors.append("external_task_id is required")

        if not self.framework:
            errors.append("framework is required")

        if not self.trigger_source:
            errors.append("trigger_source is required")

        if not self.created_by:
            errors.append("created_by is required")

        if not self.case_ids:
            errors.append("case_ids cannot be empty")

        if not isinstance(self.case_ids, list):
            errors.append("case_ids must be a list")

        if len(set(self.case_ids)) != len(self.case_ids):
            errors.append("case_ids must not contain duplicates")

        return errors