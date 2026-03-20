"""
需求与用例定义层 - 自动化测试用例模型
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ConfigDict
from beanie import Document, before_event, Save, Insert
from pymongo import IndexModel, ASCENDING, DESCENDING


class ConfigFieldModel(BaseModel):
    """自动化配置字段定义。"""
    __test__ = False

    type_marker: Optional[str] = Field(default=None, alias="__type__", description="原始类型标记")
    name: str = Field(..., description="字段名")
    label: Optional[str] = Field(None, description="字段展示名称")
    type: str = Field(..., description="字段类型")
    default: Optional[Any] = Field(None, description="默认值")
    required: bool = Field(default=False, description="是否必填")
    options: Optional[List[Any]] = Field(default=None, description="可选项")
    extensions: Optional[List[Any]] = Field(default=None, description="文件扩展名约束")
    description: Optional[str] = Field(None, description="字段描述")
    extra_props: Dict[str, Any] = Field(default_factory=dict, description="额外属性")

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ScriptRefModel(BaseModel):
    """脚本定位信息。"""
    entity_id: str = Field(..., description="脚本/配置实体定位")
    module: Optional[str] = Field(None, description="自动化模块")
    project_tag: Optional[str] = Field(None, description="项目标签")
    project_scope: Optional[str] = Field(None, description="项目作用域")


class CodeSnapshotModel(BaseModel):
    """代码版本快照。"""
    version: str = Field(..., description="脚本版本标识")
    commit_id: Optional[str] = Field(None, description="完整提交 ID")
    commit_short_id: Optional[str] = Field(None, description="短提交 ID")
    branch: Optional[str] = Field(None, description="分支名")
    author: Optional[str] = Field(None, description="提交作者")
    commit_time: Optional[datetime] = Field(None, description="提交时间")
    message: Optional[str] = Field(None, description="提交说明")


class ReportMetaModel(BaseModel):
    """上报补充信息。"""
    requirement_id: Optional[str] = Field(None, description="框架侧需求标识")
    author: Optional[str] = Field(None, description="用例作者")
    timeout: Optional[int] = Field(None, description="默认超时时间（秒）")


class AutomationTestCaseDoc(Document):
    """自动化测试用例库 - 仅保留最新可执行版本。"""
    __test__ = False

    auto_case_id: str = Field(..., description="平台自动化用例业务 ID")
    dml_manual_case_id: str = Field(..., description="关联的平台手工测试用例 ID")
    name: str = Field(..., description="自动化用例名称")
    description: Optional[str] = Field(None, description="自动化用例描述")
    status: str = Field(default="ACTIVE", description="状态（ACTIVE/DEPRECATED）")
    framework: str = Field(..., description="上报来源框架类型")
    automation_type: Optional[str] = Field(None, description="自动化类型")
    script_ref: ScriptRefModel = Field(..., description="脚本定位信息")
    config_path: Optional[str] = Field(None, description="配置文件路径")
    script_name: Optional[str] = Field(None, description="脚本文件名")
    script_path: Optional[str] = Field(None, description="脚本文件路径")
    code_snapshot: CodeSnapshotModel = Field(..., description="代码版本快照")
    param_spec: List[ConfigFieldModel] = Field(default_factory=list, description="参数定义")
    tags: List[str] = Field(default_factory=list, description="标签")
    report_meta: ReportMetaModel = Field(default_factory=ReportMetaModel, description="精简后的上报补充信息")
    is_deleted: bool = Field(default=False, description="逻辑删除标志")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @before_event([Save, Insert])
    def update_updated_at(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "automation_test_cases"
        indexes = [
            IndexModel([("auto_case_id", ASCENDING)], unique=True),
            IndexModel([("dml_manual_case_id", ASCENDING)], unique=True),
            IndexModel("status"),
            IndexModel("framework"),
            IndexModel("automation_type"),
            IndexModel("script_ref.entity_id"),
            IndexModel("script_path"),
            IndexModel("code_snapshot.version"),
            IndexModel("is_deleted"),
            IndexModel([("auto_case_id", ASCENDING), ("updated_at", DESCENDING)]),
            IndexModel("created_at"),
            IndexModel([("tags", ASCENDING), ("created_at", DESCENDING)]),
        ]


class AutomationTestCaseModel(BaseModel):
    """自动化测试用例 API 响应模型。"""
    __test__ = False

    id: Optional[str] = None
    auto_case_id: str
    dml_manual_case_id: str
    name: str
    description: Optional[str] = None
    status: str
    framework: str
    automation_type: Optional[str] = None
    script_ref: ScriptRefModel
    config_path: Optional[str] = None
    script_name: Optional[str] = None
    script_path: Optional[str] = None
    code_snapshot: CodeSnapshotModel
    param_spec: List[ConfigFieldModel] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    report_meta: ReportMetaModel = Field(default_factory=ReportMetaModel)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
