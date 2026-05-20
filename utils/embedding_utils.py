"""Embedding 适配器占位。

后续文档片段、题目和课程实体都需要通过这里生成向量。基础阶段只约定输入
输出形态：一组文本进入，返回同长度的向量列表。
"""

from utils.errors import AdapterNotConfiguredError


class EmbeddingClient:
    """文本向量化客户端占位。"""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量生成文本向量。

        真实实现需要保证返回向量数量与输入文本数量一致，并符合配置中的
        `embedding_dim` 维度约定。
        """
        raise AdapterNotConfiguredError(
            "Embedding adapter is a foundation placeholder; configure a real client first."
        )
