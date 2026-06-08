"""用例集合领域异常定义。"""


class CollectionError(Exception):
    """用例集合领域异常基类。"""


class CollectionNotFoundError(CollectionError):
    """集合不存在。"""


class CollectionNameConflictError(CollectionError):
    """集合名称重复。"""
