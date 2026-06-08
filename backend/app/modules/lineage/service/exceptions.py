"""血缘图谱领域异常定义。"""


class LineageError(Exception):
    """血缘图谱领域异常基类。"""


class UnsupportedEntityTypeError(LineageError):
    """不支持的实体类型。"""
