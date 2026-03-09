"""测试规格领域异常"""


class TestSpecsError(Exception):
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