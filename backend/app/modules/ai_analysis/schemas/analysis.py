"""AI 分析 Pydantic Schemas"""
from typing import Optional

from pydantic import BaseModel, Field


class AnalysisIssue(BaseModel):
    """分析问题项"""

    case_id: str = Field(..., description="用例ID")
    field: str = Field(..., description="问题字段")
    severity: str = Field(..., description="严重级别: critical/warning/info")
    message: str = Field(..., description="问题描述")


class DuplicatePair(BaseModel):
    """重复用例对"""

    case_id1: str = Field(..., description="用例1 ID")
    case_id2: str = Field(..., description="用例2 ID")
    similarity: float = Field(..., ge=0, le=1, description="相似度 0-1")
    reason: str = Field(..., description="重复原因")


class QualityAnalysis(BaseModel):
    """质量分析结果"""

    score: int = Field(..., ge=0, le=100, description="质量评分 0-100")
    issues: list[AnalysisIssue] = Field(default_factory=list)


class RedundancyAnalysis(BaseModel):
    """冗余检测结果"""

    score: int = Field(..., ge=0, le=100, description="冗余评分（越高越不冗余）")
    duplicates: list[DuplicatePair] = Field(default_factory=list)


class CoverageAnalysis(BaseModel):
    """覆盖率分析结果"""

    score: int = Field(..., ge=0, le=100, description="覆盖评分")
    gaps: list[str] = Field(default_factory=list, description="测试盲区描述")


class CollectionAnalysisResult(BaseModel):
    """用例集分析完整结果"""

    collection_id: str = Field(..., description="集合ID")
    overall_score: int = Field(..., ge=0, le=100, description="综合评分")
    quality: QualityAnalysis = Field(..., description="质量分析")
    redundancy: RedundancyAnalysis = Field(..., description="冗余检测")
    coverage: CoverageAnalysis = Field(..., description="覆盖率分析")
    recommendations: list[str] = Field(default_factory=list, description="改进建议")


class AnalyzeRequest(BaseModel):
    """分析请求"""

    analysis_types: list[str] = Field(
        default=["quality", "redundancy", "coverage"],
        description="分析类型: quality/redundancy/coverage",
    )
