"""执行计划命令数据类。

命令对象的定义已从本模块移除。PlanCommandService 的方法直接接受
原始参数（Dict、Pydantic request 对象等），无需额外的 Command 包装类。

如果未来需要强类型输入契约，可在此处重新引入 Command dataclass，
并将其用作 PlanCommandService 方法签名的参数类型。
"""
