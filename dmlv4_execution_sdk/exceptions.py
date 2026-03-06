"""SDK 异常定义"""

class DMLV4SDKError(Exception):
    """SDK 基础异常"""
    pass


class ReporterConfigError(DMLV4SDKError):
    """配置错误"""
    pass


class ReporterValidationError(DMLV4SDKError):
    """数据校验失败"""
    pass


class ReporterAuthError(DMLV4SDKError):
    """认证失败"""
    pass


class ReporterDeliveryError(DMLV4SDKError):
    """消息投递失败"""
    pass


class TaskNotFoundError(DMLV4SDKError):
    """任务不存在"""
    pass


class InvalidStatusError(DMLV4SDKError):
    """无效状态值"""
    pass


class SignatureError(DMLV4SDKError):
    """签名验证失败"""
    pass


class NetworkError(DMLV4SDKError):
    """网络请求失败"""
    pass