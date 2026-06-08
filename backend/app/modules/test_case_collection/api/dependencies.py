"""用例集合 API 依赖注入。"""
from typing import Annotated

from fastapi import Depends

from app.modules.test_case_collection.service import TestCaseCollectionService


async def get_collection_service() -> TestCaseCollectionService:
    return TestCaseCollectionService()


CollectionServiceDep = Annotated[
    TestCaseCollectionService,
    Depends(get_collection_service),
]
