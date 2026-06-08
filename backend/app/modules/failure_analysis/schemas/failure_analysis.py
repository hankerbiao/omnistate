"""失效分析数据模型。"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

FailurePattern = str
"""失败模式类型: TIMEOUT | ASSERTION_ERROR | ENV_SETUP | DEPENDENCY | CONFIG_ERROR | NETWORK_ERROR | HARDWARE_ERROR | MEMORY_ERROR | SCRIPT_ERROR | UNKNOWN"""


class FailurePatternSummary(BaseModel):
    """失败模式统计摘要。"""
    pattern: FailurePattern
    count: int
    percentage: float


class FailureByAgent(BaseModel):
    """按代理统计的失败分布。"""
    agent_id: str
    hostname: str
    failure_count: int
    pattern_breakdown: Dict[FailurePattern, int]


class FailureDailyTrend(BaseModel):
    """每日失败趋势。"""
    date: str  # YYYY-MM-DD
    failure_count: int
    patterns: Dict[FailurePattern, int]


class FlakyTestCase(BaseModel):
    """不稳定测试用例。"""
    auto_case_id: str
    case_id: str
    name: str
    total_runs: int
    flaky_ratio: float
    recent_results: List[Dict[str, Any]]


class HighFrequencyFailure(BaseModel):
    """高频失败测试用例。"""
    auto_case_id: str
    case_id: str
    name: str
    failure_count: int
    dominant_pattern: FailurePattern
    latest_failure_at: Optional[datetime] = None
    avg_duration_sec: Optional[float] = None


class FailureAnalysisDashboard(BaseModel):
    """失效分析仪表盘聚合数据。"""
    time_range: str
    total_failures: int
    pattern_distribution: List[FailurePatternSummary] = []
    by_agent: List[FailureByAgent] = []
    daily_trend: List[FailureDailyTrend] = []
    flaky_tests: List[FlakyTestCase] = []
    high_frequency_failures: List[HighFrequencyFailure] = []
