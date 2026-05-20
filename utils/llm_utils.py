"""LLM 适配器占位。

基础阶段只固定调用边界，不直接接入真实大模型服务。后续可以在该模块内部
替换为 DashScope、OpenAI 兼容接口或其他厂商 SDK，而不影响上层业务。
"""

from utils.errors import AdapterNotConfiguredError


class LLMClient:
    """文本生成客户端占位。

    真实实现应负责 prompt 发送、超时控制、异常包装、日志脱敏和模型参数管理。
    """

    def generate(self, prompt: str) -> str:
        """生成文本回答。

        当前阶段故意抛出异常，提醒调用方不要把占位实现当成真实模型结果。
        """
        raise AdapterNotConfiguredError(
            "LLM adapter is a foundation placeholder; configure a real client first."
        )
