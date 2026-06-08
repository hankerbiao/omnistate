"""失效分析领域异常定义。"""


class FailureAnalysisError(Exception):
    """失效分析领域异常基类。"""


class EntityNotFoundError(FailureAnalysisError):
    """查询的实体不存在。"""
