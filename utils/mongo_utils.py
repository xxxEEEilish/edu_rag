"""MongoDB 适配器占位。

MongoDB 后续用于保存课程、章节、题目、文档、片段、导入任务和会话历史等
结构化数据。基础阶段只提供统一入口，避免其他模块直接依赖具体驱动。
"""

from utils.errors import AdapterNotConfiguredError


class MongoClientProvider:
    """MongoDB 数据库连接提供者占位。"""

    def get_database(self) -> object:
        """返回数据库对象。

        真实实现应在这里处理连接复用、数据库名选择和连接失败异常包装。
        """
        raise AdapterNotConfiguredError(
            "MongoDB adapter is a foundation placeholder; configure a real client first."
        )
