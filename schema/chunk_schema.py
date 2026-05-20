"""知识片段和引用来源 Schema。

知识片段是导入、索引、检索和答案引用之间的核心数据结构。这里保留课程、
章节、项目、来源文件、租户、版本和哈希等追溯字段，确保后续答案能回到
原始材料。
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from core.enums import ContentType, SourceType


def utc_now() -> datetime:
    """生成带时区的 UTC 时间。

    使用 timezone-aware datetime 可以减少跨时区部署和日志排序时的歧义。
    """
    return datetime.now(timezone.utc)


class ReferenceSource(BaseModel):
    """查询答案中的引用来源。

    每个引用都描述召回内容来自哪里，以及相关性分数等调试信息。前端展示引用
    和后续人工复核都会依赖这个结构。
    """

    source_type: SourceType
    content_type: ContentType
    course_name: str | None = None
    chapter_name: str | None = None
    project_name: str | None = None
    source_file_name: str | None = None
    source_path: str | None = None
    page_no: int | None = None
    score: float | None = None


class KnowledgeChunk(BaseModel):
    """可检索的知识片段。

    该模型面向 Milvus 向量记录和 MongoDB 元数据记录的公共字段设计。
    一期主要保存文档片段，后续也可以复用到课程介绍、项目资料和视频字幕。
    """

    chunk_id: str
    content: str
    content_type: ContentType = ContentType.DOCUMENT_CHUNK
    # 课程、章节、项目字段用于元数据过滤和结果追溯。
    course_id: str | None = None
    course_name: str
    chapter_id: str | None = None
    chapter_name: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    knowledge_points: list[str] = Field(default_factory=list)
    # 来源字段是答案可复核的关键，导入阶段必须尽量补齐。
    source_file_name: str
    source_path: str
    page_no: int | None = None
    # version/content_hash/is_active 为后续增量更新和软删除预留。
    version: str = "v1"
    tenant_id: str = "default"
    is_active: bool = True
    content_hash: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
