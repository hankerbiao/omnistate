"""执行任务请求命令。"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime



@dataclass
class DispatchExecutionTaskCommand:
    """分发执行任务命令。"""
    # 任务基本信息
    task_id: str
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
    framework: Optional[str] = None
    trigger_source: Optional[str] = None
    category: Optional[str] = None
    project_tag: Optional[str] = None
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    pytest_options: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = None
    attachments: Optional[List[Dict[str, Any]]] = None

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
        from app.shared.config import get_settings
        execution_cfg = get_settings().execution
        if self.repo_url is None:
            self.repo_url = execution_cfg.default_repo_url or None
        if self.branch is None:
            self.branch = execution_cfg.default_branch
        if self.category is None:
            self.category = ""
        if self.project_tag is None:
            self.project_tag = ""
        if self.pytest_options is None:
            self.pytest_options = {}
        if self.timeout is None:
            self.timeout = 0
        if self.attachments is None:
            self.attachments = []

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
    def dispatch_task_data(self) -> Dict[str, Any]:
        """按需构建发送到执行端的任务数据，避免命令被更新后缓存失效。"""
        return self._build_dispatch_task_data()

    def _build_dispatch_task_data(self) -> Dict[str, Any]:
        """构建统一的任务下发数据。"""
        current_case_id = self.dispatch_case_id
        current_case_payload = self.case_payloads[self.dispatch_case_index]
        from app.shared.kafka import load_kafka_config
        kafka_cfg = load_kafka_config()
        pytest_defaults = {
            "log_debug": False,
            "kafka_server": ",".join(kafka_cfg.bootstrap_servers),
            "kafka_topic": kafka_cfg.test_events_topic,
            "report_kafka": True,
            "maxfail": "3",
            "task_id": self.task_id,
        }
        pytest_options = {**pytest_defaults, **self.pytest_options}
        script_path = current_case_payload.get("script_path")
        script_name = current_case_payload.get("script_name")
        case_parameters = dict(current_case_payload.get("parameters") or {})
        # Refresh download URLs for file-type params (URLs may have expired since stored)
        case_parameters = self._refresh_file_param_urls(case_parameters)
        if not script_path:
            raise ValueError(f"script_path is required for dispatch case: {current_case_id}")
        if not script_name:
            raise ValueError(f"script_name is required for dispatch case: {current_case_id}")
        return {
            "task_id": self.task_id,
            "framework": self.framework,
            "trigger_source": self.trigger_source,
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

    @staticmethod
    def _refresh_file_param_urls(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Regenerate download URLs for file-type parameters. Gracefully handles MinIO failures."""
        result = dict(parameters)
        from app.shared.minio import get_minio_client
        try:
            minio_client = get_minio_client()
            for key, value in result.items():
                if isinstance(value, dict) and value.get("type") == "file" and "object_name" in value:
                    result[key] = {
                        **value,
                        "download_url": minio_client.presigned_get_object(value["object_name"]),
                    }
        except Exception:
            pass  # Keep existing URLs if MinIO refresh fails
        return result
