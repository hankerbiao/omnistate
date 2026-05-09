"""DUT 服务依赖注入"""
from typing import Annotated

from fastapi import Depends

from app.modules.assets.service import DutService


def get_dut_service() -> DutService:
    """获取 DUT 服务实例"""
    return DutService()


DutServiceDep = Annotated[DutService, Depends(get_dut_service)]