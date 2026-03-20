"""执行任务请求命令。"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.modules.execution.application.constants import (
    DEFAULT_EXECUTION_BRANCH,
    DEFAULT_EXECUTION_REPO_URL,
)


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
    auto_case_ids: List[str]
    case_ids: List[str]
    script_entity_ids: Optional[List[Optional[str]]] = None
    case_configs: Optional[List[Dict[str, Any]]] = None
    case_payloads: Optional[List[Dict[str, Any]]] = None
    dispatch_case_id: Optional[str] = None
    dispatch_auto_case_id: Optional[str] = None
    dispatch_script_entity_id: Optional[str] = None
    dispatch_case_config: Optional[Dict[str, Any]] = None
    dispatch_case_index: int = 0
    dispatch_channel: Optional[str] = None
    agent_id: Optional[str] = None
    schedule_type: str = "IMMEDIATE"
    planned_at: Optional[datetime] = None

    # 任务配置
    callback_url: Optional[str] = None
    category: Optional[str] = None
    project_tag: Optional[str] = None
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    common_parameters: Optional[Dict[str, Any]] = None
    pytest_options: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    dut: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.script_entity_ids is None:
            self.script_entity_ids = [None] * len(self.case_ids)
        if self.case_configs is None:
            self.case_configs = [{} for _ in self.case_ids]
        if self.case_payloads is None:
            self.case_payloads = [{} for _ in self.case_ids]
        if self.dispatch_case_id is None and len(self.case_ids) == 1:
            self.dispatch_case_id = self.case_ids[0]
        if self.dispatch_auto_case_id is None and len(self.auto_case_ids) == 1:
            self.dispatch_auto_case_id = self.auto_case_ids[0]
        if self.dispatch_script_entity_id is None and len(self.script_entity_ids) == 1:
            self.dispatch_script_entity_id = self.script_entity_ids[0]
        if self.dispatch_case_config is None and len(self.case_configs) == 1:
            self.dispatch_case_config = self.case_configs[0]

    @property
    def kafka_task_data(self) -> Dict[str, Any]:
        """按需构建发送到 Kafka/HTTP 的任务数据，避免命令被更新后缓存失效。"""
        return self._build_kafka_task_data()

    def _build_kafka_task_data(self) -> Dict[str, Any]:
        """构建Kafka任务数据"""
        current_case_id = self.dispatch_case_id or self.case_ids[0]
        current_auto_case_id = self.dispatch_auto_case_id or self.auto_case_ids[0]
        current_script_entity_id = self.dispatch_script_entity_id
        current_case_config = self.dispatch_case_config
        current_case_payload = self.case_payloads[self.dispatch_case_index] if self.case_payloads else {}
        if current_script_entity_id is None and self.script_entity_ids:
            current_script_entity_id = self.script_entity_ids[self.dispatch_case_index]
        if current_case_config is None and self.case_configs:
            current_case_config = self.case_configs[self.dispatch_case_index]
        pytest_defaults = {
            "log_debug": False,
            "kafka_servers": "10.17.154.252:9092",
            "kafka_topic": "test-events",
            "report_kafka": True,
            "maxfail": "3",
            "task_id": self.task_id,
        }
        pytest_options = {**pytest_defaults, **(self.pytest_options or {})}
        return {
            "task_id": self.task_id,
            "category": self.category or "",
            "project_tag": self.project_tag or "",
            "repo_url": self.repo_url or DEFAULT_EXECUTION_REPO_URL,
            "branch": self.branch or DEFAULT_EXECUTION_BRANCH,
            "cases": [{
                "case_id": current_case_payload.get("case_id") or current_case_id,
                "case_path": current_case_payload.get("case_path") or current_script_entity_id or "",
                "case_name": current_case_payload.get("case_name") or current_auto_case_id or current_case_id,
                "parameters": current_case_payload.get("parameters") or current_case_config or {},
            }],
            "common_parameters": self.common_parameters or {},
            "pytest_options": pytest_options,
            "timeout": self.timeout or 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
