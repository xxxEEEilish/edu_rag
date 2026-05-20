"""MinIO 适配器占位。

MinIO 后续用于保存原始上传文件、解析后的 Markdown、课件图片、视频关键帧
和导出结果。基础阶段只定义客户端入口，避免启动时要求对象存储可用。
"""

from utils.errors import AdapterNotConfiguredError


class MinioClientProvider:
    """MinIO 客户端提供者占位。"""

    def get_client(self) -> object:
        """返回对象存储客户端。

        真实实现应处理 bucket 初始化、路径规范、上传下载和权限错误包装。
        """
        raise AdapterNotConfiguredError(
            "MinIO adapter is a foundation placeholder; configure a real client first."
        )
