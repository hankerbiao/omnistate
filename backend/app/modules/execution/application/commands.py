"""执行任务请求命令。"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime

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
    source_task_id: Optional[str] = None
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
    pytest_options: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    dut: Optional[Dict[str, Any]] = None

    def _initialize_case_collections(self) -> None:
        if self.script_entity_ids is None:
            self.script_entity_ids = [None] * len(self.case_ids)
        if self.case_configs is None:
            self.case_configs = [{} for _ in self.case_ids]
        if self.case_payloads is None:
            self.case_payloads = [{} for _ in self.case_ids]

    def _validate_case_collection_lengths(self) -> None:
        if len(self.auto_case_ids) != len(self.case_ids):
            raise ValueError("auto_case_ids length must match case_ids length")
        if len(self.script_entity_ids) != len(self.case_ids):
            raise ValueError("script_entity_ids length must match case_ids length")
        if len(self.case_configs) != len(self.case_ids):
            raise ValueError("case_configs length must match case_ids length")
        if len(self.case_payloads) != len(self.case_ids):
            raise ValueError("case_payloads length must match case_ids length")

    def _apply_defaults(self) -> None:
        if self.dispatch_channel is None:
            raise ValueError("dispatch_channel is required")
        if isinstance(self.repo_url, str) and not self.repo_url.strip():
            self.repo_url = None
        if isinstance(self.branch, str) and not self.branch.strip():
            self.branch = None
        if self.repo_url is None:
            self.repo_url = DEFAULT_EXECUTION_REPO_URL
        if self.branch is None:
            self.branch = DEFAULT_EXECUTION_BRANCH
        if self.category is None:
            self.category = ""
        if self.project_tag is None:
            self.project_tag = ""
        if self.pytest_options is None:
            self.pytest_options = {}
        if self.timeout is None:
            self.timeout = 0

    def _initialize_dispatch_targets(self) -> None:
        if self.dispatch_case_id is None:
            self.dispatch_case_id = self.case_ids[self.dispatch_case_index]
        if self.dispatch_auto_case_id is None:
            self.dispatch_auto_case_id = self.auto_case_ids[self.dispatch_case_index]
        if self.dispatch_script_entity_id is None:
            self.dispatch_script_entity_id = self.script_entity_ids[self.dispatch_case_index]
        if self.dispatch_case_config is None:
            self.dispatch_case_config = self.case_configs[self.dispatch_case_index]

    def __post_init__(self):
        """初始化后处理"""
        self._initialize_case_collections()
        self._validate_case_collection_lengths()
        self._apply_defaults()
        self._initialize_dispatch_targets()

    @property
    def kafka_task_data(self) -> Dict[str, Any]:
        """按需构建发送到 Kafka/HTTP 的任务数据，避免命令被更新后缓存失效。"""
        return self._build_kafka_task_data()

    def _build_kafka_task_data(self) -> Dict[str, Any]:
        """构建Kafka任务数据"""
        current_case_id = self.dispatch_case_id
        current_case_config = self.dispatch_case_config
        current_case_payload = self.case_payloads[self.dispatch_case_index]
        pytest_defaults = {
            "log_debug": False,
            "kafka_server": "10.17.154.252:9092",
            "kafka_topic": "test-events",
            "report_kafka": True,
            "maxfail": "3",
            "task_id": self.task_id,
        }
        pytest_options = {**pytest_defaults, **self.pytest_options}
        script_path = current_case_payload.get("script_path")
        script_name = current_case_payload.get("script_name")
        case_parameters = current_case_payload.get("parameters")
        if not script_path:
            raise ValueError(f"script_path is required for dispatch case: {current_case_id}")
        if not script_name:
            raise ValueError(f"script_name is required for dispatch case: {current_case_id}")
        if case_parameters is None:
            case_parameters = current_case_config
        case_parameters = {
            **dict(case_parameters or {}),
            "script_path": script_path,
            "script_name": script_name,
        }
        return {
            "task_id": self.task_id,
            "category": self.category,
            "project_tag": self.project_tag,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "cases": [{
                "case_id": current_case_payload["case_id"],
                "script_path": script_path,
                "script_name": script_name,
                "parameters": case_parameters,
            }],
            "pytest_options": pytest_options,
            "timeout": self.timeout,
        }
