"""工具层异常定义。

适配器占位阶段需要清晰地告诉调用方“能力尚未接入”，避免返回空结果造成
后续业务误判为检索无结果或模型正常返回。
"""


class AdapterNotConfiguredError(RuntimeError):
    """外部服务适配器尚未配置时抛出的异常。"""
