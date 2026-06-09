"""测试规格领域异常"""

from app.shared.domain.exceptions import AppError


class TestSpecsError(AppError):
    """测试规格基础异常"""
    pass


class RequirementNotFoundError(TestSpecsError):
    """需求不存在异常"""

    def __init__(self, req_id: str):
        super().__init__(f"需求 ID={req_id} 不存在")


class TestCaseNotFoundError(TestSpecsError):
    """测试用例不存在异常"""

    def __init__(self, case_id: str):
        super().__init__(f"测试用例 ID={case_id} 不存在")


class CatalogPathValidationError(TestSpecsError):
    """目录路径段校验失败"""

    def __init__(self, message: str):
        super().__init__(message)


class LabNotFoundError(TestSpecsError):
    """Lab 不存在"""

    def __init__(self, lab_id: str):
        super().__init__(f"Lab ID={lab_id} 不存在")


class LabConflictError(TestSpecsError):
    """Lab 业务冲突（重复 code、仍有下属用例等）"""

    def __init__(self, message: str):
        super().__init__(message)
