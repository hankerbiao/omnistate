"""失败模式分类器（基于规则的正则匹配）。

对测试执行失败消息进行自动分类，识别失败根因模式。
返回统一的 FailurePattern 类型标识。
"""
import re
from typing import Optional


class FailurePatternClassifier:
    """
    基于规则的失败模式分类器。

    按顺序匹配正则规则，首个命中即返回对应模式。
    无匹配则返回 UNKNOWN。

    使用方式：
        pattern = FailurePatternClassifier.classify(failure_message)
    """

    RULES: list[tuple[str, list[str]]] = [
        # (pattern_label, [regex_patterns])
        ("TIMEOUT", [
            r"timeout", r"timed?\s*out", r"duration.*exceed",
            r"deadline.*exceed", r"killed", r"socket\.timeout",
            r"connect timeout", r"wait.*timeout",
        ]),
        ("ASSERTION_ERROR", [
            r"assertion\s*error", r"assert", r"expected.*but got",
            r"expected.*actual", r"assertion failed", r"assertTrue",
            r"assertEqual", r"assertIn", r"expect.*to.*be",
            r"should.*equal", r"value.*mismatch",
        ]),
        ("ENV_SETUP", [
            r"environment.*setup", r"setup.*failed", r"teardown.*failed",
            r"fixture.*error", r"conftest", r"env.*not.*found",
            r"no such file", r"file.*not found", r"directory.*not found",
            r"permission denied",
        ]),
        ("DEPENDENCY", [
            r"module.*not found", r"import.*error", r"cannot import",
            r"no module named", r"dependency", r"package.*not.*found",
            r"pip.*install", r"missing.*dependency",
        ]),
        ("CONFIG_ERROR", [
            r"configuration.*error", r"config.*invalid", r"invalid.*parameter",
            r"missing.*config", r"wrong.*config", r"bad.*config",
            r"param.*error", r"invalid.*argument",
        ]),
        ("NETWORK_ERROR", [
            r"network.*error", r"connection.*refused", r"connection.*reset",
            r"connection.*timed out", r"cannot connect", r"dns.*error",
            r"no route to host", r"broken pipe", r"ssl.*error",
        ]),
        ("HARDWARE_ERROR", [
            r"hardware.*error", r"device.*not.*found", r"dut.*error",
            r"i2c.*error", r"spi.*error", r"pcie.*error", r"dimm.*error",
            r"memory.*error", r"register.*error", r"sensor.*error",
            r"fan.*error", r"power.*error", r"temperature",
        ]),
        ("MEMORY_ERROR", [
            r"out of memory", r"oom", r"memory.*allocation", r"cannot allocate",
            r"memory.*exhaust", r"malloc.*failed", r"stack overflow",
            r"heap.*exhaust", r"memory.*leak",
        ]),
        ("SCRIPT_ERROR", [
            r"syntax.*error", r"type.?error", r"key.?error", r"index.?error",
            r"attribute.?error", r"value.?error", r"name.?error",
            r"runtime.*error", r"traceback", r"exception",
            r"division by zero", r"null pointer", r"segmentation fault",
        ]),
    ]

    PATTERN_LABELS: dict[str, str] = {
        "TIMEOUT": "超时",
        "ASSERTION_ERROR": "断言失败",
        "ENV_SETUP": "环境异常",
        "DEPENDENCY": "依赖缺失",
        "CONFIG_ERROR": "配置错误",
        "NETWORK_ERROR": "网络异常",
        "HARDWARE_ERROR": "硬件异常",
        "MEMORY_ERROR": "内存错误",
        "SCRIPT_ERROR": "脚本错误",
        "UNKNOWN": "未识别",
    }

    @classmethod
    def classify(cls, failure_message: Optional[str]) -> str:
        """对失败消息分类，返回 FailurePattern 类型字符串。

        Args:
            failure_message: 失败消息文本，可能为 None 或空字符串。

        Returns:
            匹配的模式标识，如 "TIMEOUT", "ASSERTION_ERROR" 等。
            无匹配时返回 "UNKNOWN"。
        """
        if not failure_message or not failure_message.strip():
            return "UNKNOWN"

        normalized = failure_message.lower().strip()

        for pattern_label, regexes in cls.RULES:
            for regex in regexes:
                if re.search(regex, normalized):
                    return pattern_label

        return "UNKNOWN"

    @classmethod
    def get_label(cls, pattern: str) -> str:
        """获取模式的中文标签。"""
        return cls.PATTERN_LABELS.get(pattern, pattern)
