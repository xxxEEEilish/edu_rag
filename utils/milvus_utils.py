"""Milvus 适配器占位。

Milvus 后续承担文档片段、题目、课程实体、视频片段和多模态资产的向量检索。
基础阶段不创建集合、不连接服务，只声明统一客户端入口。
"""

from utils.errors import AdapterNotConfiguredError


class MilvusClientProvider:
    """Milvus 客户端提供者占位。"""

    def get_client(self) -> object:
        """返回向量库客户端。

        后续真实实现应根据配置管理集合名、索引参数和连接生命周期。
        """
        raise AdapterNotConfiguredError(
            "Milvus adapter is a foundation placeholder; configure a real client first."
        )
