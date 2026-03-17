"""执行任务请求命令。"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class DispatchExecutionTaskCommand:
    """分发执行任务命令。"""
    # 任务基本信息
    task_id: str
    external_task_id: str
    framework: str
    trigger_source: str
    created_by: str

    # 测试用例信息
    case_ids: List[str]
    run_no: int = 1
    dispatch_case_id: Optional[str] = None
    dispatch_case_index: int = 0
    agent_id: Optional[str] = None
    schedule_type: str = "IMMEDIATE"
    planned_at: Optional[datetime] = None

    # 任务配置
    callback_url: Optional[str] = None
    dut: Optional[Dict[str, Any]] = None
    runtime_config: Optional[Dict[str, Any]] = None

    # 发送到 Kafka 的任务数据，由命令对象统一构建
    kafka_task_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.dispatch_case_id is None and len(self.case_ids) == 1:
            self.dispatch_case_id = self.case_ids[0]
        if self.kafka_task_data is None:
            self.kafka_task_data = self._build_kafka_task_data()

    def _build_kafka_task_data(self) -> Dict[str, Any]:
        """构建Kafka任务数据"""
        current_case_id = self.dispatch_case_id or self.case_ids[0]
        return {
            "task_id": self.task_id,
            "external_task_id": self.external_task_id,
            "framework": self.framework,
            "trigger_source": self.trigger_source,
            "agent_id": self.agent_id,
            "schedule_type": self.schedule_type,
            "planned_at": self.planned_at.isoformat() if self.planned_at else None,
            "callback_url": self.callback_url,
            "dut": self.dut or {},
            "cases": [{"case_id": current_case_id}],
            "run_no": self.run_no,
            "current_case_id": current_case_id,
            "current_case_index": self.dispatch_case_index,
            "case_count": len(self.case_ids),
            "runtime_config": self.runtime_config or {},
            "created_by": self.created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
