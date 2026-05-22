"""执行任务请求命令。"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class DispatchExecutionTaskCommand:
    """分发执行任务命令。

    纯数据容器，不包含验证/构建逻辑。
    所有初始化、验证、构建逻辑由 TaskCommandBuilder 处理。
    """
    # 任务基本信息
    task_id: str
    created_by: str

    # 测试用例信息
    auto_case_ids: List[str]
    case_ids: List[str]
    source_task_id: Optional[str] = None
    agent_id: Optional[str] = None
    script_entity_ids: Optional[List[Optional[str]]] = None
    case_configs: Optional[List[Dict[str, Any]]] = None
    case_payloads: Optional[List[Dict[str, Any]]] = None
    dispatch_case_id: Optional[str] = None
    dispatch_auto_case_id: Optional[str] = None
    dispatch_script_entity_id: Optional[str] = None
    dispatch_case_config: Optional[Dict[str, Any]] = None
    dispatch_case_index: int = 0
    dispatch_channel: Optional[str] = None
    schedule_type: str = "IMMEDIATE"
    planned_at: Optional[datetime] = None

    # 任务配置
    trigger_source: Optional[str] = None
    category: Optional[str] = None
    project_tag: Optional[str] = None
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    pytest_options: Optional[Dict[str, Any]] = field(default_factory=dict)
    timeout: Optional[int] = None
    attachments: Optional[List[Dict[str, Any]]] = field(default_factory=list)

    is_proxy: bool = True  # 是否为代理命令，默认为 False
    nc_pypi: str = 'http://10.2.48.111:8080/simple'
