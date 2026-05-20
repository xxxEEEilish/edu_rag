"""导入任务 Schema。

导入任务用于跟踪上传文件从接收、解析、切片、向量化到入库的生命周期。
基础阶段只定义数据契约，真实任务编排将在后续导入链路变更中实现。
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from core.enums import ContentType, ImportTaskStatus


def utc_now() -> datetime:
    """生成带时区的 UTC 时间，便于跨服务记录任务状态变化。"""
    return datetime.now(timezone.utc)


class ImportTask(BaseModel):
    """单个文件或导入批次的状态记录。

    该模型既可用于 API 响应，也可用于 MongoDB 中的任务元数据。`progress`
    使用 0-100 的闭区间，方便前端直接展示进度条。
    """

    task_id: str
    status: ImportTaskStatus = ImportTaskStatus.PENDING
    file_name: str
    content_type: ContentType | None = None
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    error: str | None = None
    course_name: str | None = None
    chapter_name: str | None = None
    project_name: str | None = None
    tenant_id: str = "default"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
