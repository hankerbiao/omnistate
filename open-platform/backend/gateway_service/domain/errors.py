"""网关统一异常。

管线各阶段抛出的都是 ``GatewayError``，由路由层统一转换为 ``common.responses.build_gateway_error_response``。
把「错误码 / 诊断 / HTTP 状态码」的映射收敛到一处，新增错误类型时无需改动路由处理函数。
"""

from __future__ import annotations


class GatewayError(Exception):
    """网关在处理请求过程中主动拒绝或上游不可用时抛出。"""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        diagnosis: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.diagnosis = diagnosis
        super().__init__(message)
