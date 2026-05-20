"""Reranker 适配器占位。

检索链路会先召回候选片段，再用重排模型提高相关性排序。这里先固定接口，
后续真实实现只需返回与候选文档一一对应的分数列表。
"""

from utils.errors import AdapterNotConfiguredError


class RerankerClient:
    """候选文档重排客户端占位。"""

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        """根据查询对候选文档打分。

        当前阶段不提供真实分数，避免上层误以为重排模型已接入。
        """
        raise AdapterNotConfiguredError(
            "Reranker adapter is a foundation placeholder; configure a real client first."
        )
