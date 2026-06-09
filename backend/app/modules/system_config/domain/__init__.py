# Domain exceptions
class ConfigNotFoundError(Exception):
    """配置不存在"""
    pass


class ConfigValidationError(Exception):
    """配置验证失败"""
    pass


class ConfigEncryptionError(Exception):
    """配置加密/解密失败"""
    pass
