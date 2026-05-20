"""内容导入流水线 Schema。

本模块定义 API、服务编排、解析器和存储适配器之间共享的数据契约。
这些模型刻意不绑定 MongoDB、Milvus、MinIO 或具体解析库，目的是让导入
流水线可以在单元测试中使用内存替身离线运行，也方便后续替换为生产级任务队列。
"""

from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from core.enums import ContentType, ImportTaskStatus


def utc_now() -> datetime:
    """生成带时区的 UTC 时间。

    导入任务会跨 API、后台执行器和存储系统流转，统一使用 timezone-aware
    datetime 可以减少排序、序列化和日志排查时的歧义。
    """
    return datetime.now(timezone.utc)


def stable_sha256(value: bytes | str) -> str:
    """计算稳定 SHA-256 哈希。

    源文件哈希和片段哈希都使用同一算法，便于导入幂等判断、增量更新和后续
    人工复核。字符串会按 UTF-8 编码后计算，避免调用方重复处理编码细节。
    """
    raw = value.encode("utf-8") if isinstance(value, str) else value
    return sha256(raw).hexdigest()


class ImportInputFormat(StrEnum):
    """导入源格式。

    该枚举描述解析器选择所需的格式信息，而 `ContentType` 描述进入知识库后的
    业务内容类型。两者分离后，后续同一个业务类型可以支持 PDF、DOCX、字幕等
    多种源格式。
    """

    TEXT = "text"
    MARKDOWN = "markdown"
    DOCX = "docx"
    QUESTION_JSON = "question_json"


class ImportStage(StrEnum):
    """导入任务的当前执行阶段。

    阶段字段用于比总状态更细地说明任务卡在哪里，失败时也能保留最后完成或正在
    执行的步骤，方便前端展示和运维排查。
    """

    CREATED = "created"
    STORED_SOURCE = "stored_source"
    PARSED = "parsed"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    INDEXED = "indexed"
    PERSISTED = "persisted"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    FAILED = "failed"


class ParserWarning(BaseModel):
    """解析过程中的非致命告警。

    DOCX 图片、公式、复杂排版等暂时不能完整转成文本时，应通过 warning 告知调用方，
    但不阻塞可解析文本继续入库。
    """

    code: str
    message: str
    location: str | None = None


class ImportMetadata(BaseModel):
    """导入内容的业务元数据。

    元数据会向下传播到解析结果、知识片段、题目记录和索引元数据中，是后续检索过滤、
    引用追踪、后台管理和租户隔离的基础。
    """

    tenant_id: str = "default"
    course_id: str | None = None
    course_name: str
    chapter_id: str | None = None
    chapter_name: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    knowledge_points: list[str] = Field(default_factory=list)


class ImportRequest(BaseModel):
    """内容导入请求。

    首期 API 使用 JSON 请求承载 `source_text`，避免引入 multipart 依赖；服务层仍以
    bytes 为统一输入，因此后续接入真实文件上传或对象存储回调时不需要改写流水线。
    """

    file_name: str
    input_format: ImportInputFormat | None = None
    content_type: ContentType = ContentType.DOCUMENT
    source_path: str | None = None
    source_text: str | None = None
    force_reimport: bool = False
    version: str = "v1"
    metadata: ImportMetadata

    @model_validator(mode="after")
    def validate_import_request(self) -> "ImportRequest":
        """校验导入请求的最小可执行条件。

        这里不尝试读取真实文件系统，只要求请求携带可供首期流水线处理的文本内容，
        并根据文件名补齐 source_path，确保后续存储和追踪字段稳定。
        """
        if not self.file_name.strip():
            raise ValueError("file_name 不能为空")
        if self.source_text is None:
            raise ValueError("source_text 不能为空，首期 JSON 导入需要直接提供文本内容")
        if not self.source_path:
            safe_name = PurePosixPath(self.file_name).name
            self.source_path = f"raw/{self.metadata.tenant_id}/{safe_name}"
        return self

    def source_bytes(self) -> bytes:
        """返回导入源的 UTF-8 字节表示。

        服务层和对象存储适配器都以 bytes 为边界，避免解析器、哈希计算和存储层各自
        重复处理字符串编码。
        """
        return (self.source_text or "").encode("utf-8")

    def resolved_format(self) -> ImportInputFormat:
        """根据显式格式或文件扩展名推断解析格式。"""
        if self.input_format:
            return self.input_format
        suffix = PurePosixPath(self.file_name.lower()).suffix
        if suffix == ".md":
            return ImportInputFormat.MARKDOWN
        if suffix == ".docx":
            return ImportInputFormat.DOCX
        if suffix == ".json":
            return ImportInputFormat.QUESTION_JSON
        return ImportInputFormat.TEXT


class ParsedSection(BaseModel):
    """文档解析后的有序文本段。

    解析器只负责把不同源格式转换成这种统一结构；切片器再基于该结构生成
    `KnowledgeChunk`，从而让 DOCX、Markdown 和后续 PDF 共享同一切片逻辑。
    """

    text: str
    heading_path: list[str] = Field(default_factory=list)
    order: int
    source_file_name: str
    source_path: str
    location: str | None = None
    metadata: ImportMetadata


class ParsedDocument(BaseModel):
    """文档类解析结果。"""

    file_name: str
    source_path: str
    source_hash: str
    sections: list[ParsedSection] = Field(default_factory=list)
    warnings: list[ParserWarning] = Field(default_factory=list)


class QuestionImportItem(BaseModel):
    """结构化题库导入项。

    题目数据既要保持题干、选项、答案和解析的完整性，也要带上来源字段，确保后续
    题库检索和答案引用能回到原始导入任务。
    """

    question_id: str | None = None
    question_code: str | None = None
    question_bank_name: str | None = None
    question_type: str
    stem: str
    options: list[str] = Field(default_factory=list)
    answer: str | list[str]
    analysis: str | None = None
    difficulty: str | None = None
    source_file_name: str | None = None
    source_path: str | None = None
    content_hash: str | None = None
    metadata: ImportMetadata


class ParsedQuestionSet(BaseModel):
    """题库解析结果。"""

    file_name: str
    source_path: str
    source_hash: str
    questions: list[QuestionImportItem] = Field(default_factory=list)
    warnings: list[ParserWarning] = Field(default_factory=list)


class ImportTask(BaseModel):
    """单个导入任务的状态记录。

    该模型既可作为 API 响应，也可作为元数据存储记录。阶段、进度和统计字段用于
    驱动前端状态展示；哈希、来源和元数据字段用于幂等判断与追踪。
    """

    task_id: str = Field(default_factory=lambda: f"import_{uuid4().hex}")
    status: ImportTaskStatus = ImportTaskStatus.PENDING
    stage: ImportStage = ImportStage.CREATED
    file_name: str
    source_path: str | None = None
    stored_source_path: str | None = None
    source_hash: str | None = None
    content_type: ContentType | None = None
    input_format: ImportInputFormat | None = None
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    error: str | None = None
    course_name: str | None = None
    chapter_name: str | None = None
    project_name: str | None = None
    tenant_id: str = "default"
    version: str = "v1"
    force_reimport: bool = False
    duplicate_of_task_id: str | None = None
    chunk_count: int = 0
    question_count: int = 0
    warning_count: int = 0
    imported_chunk_ids: list[str] = Field(default_factory=list)
    imported_question_ids: list[str] = Field(default_factory=list)
    warnings: list[ParserWarning] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @classmethod
    def from_request(cls, request: ImportRequest, source_hash: str) -> "ImportTask":
        """根据请求创建初始任务记录。

        该工厂集中处理请求到任务的字段映射，避免 API、服务和测试里重复拼装任务。
        """
        metadata = request.metadata
        return cls(
            file_name=request.file_name,
            source_path=request.source_path,
            source_hash=source_hash,
            content_type=request.content_type,
            input_format=request.resolved_format(),
            course_name=metadata.course_name,
            chapter_name=metadata.chapter_name,
            project_name=metadata.project_name,
            tenant_id=metadata.tenant_id,
            version=request.version,
            force_reimport=request.force_reimport,
            message="导入任务已创建，等待处理",
        )

    def touch(self) -> None:
        """刷新任务更新时间。"""
        self.updated_at = utc_now()


class ImportTaskSummary(BaseModel):
    """任务列表或提交响应中使用的轻量摘要。"""

    task_id: str
    status: ImportTaskStatus
    progress: int
    message: str
    file_name: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime


class ImportTaskDetail(ImportTask):
    """任务详情响应。

    当前详情与存储模型字段一致，单独保留类型名称是为了后续隐藏内部字段或增加展示
    计算字段时不影响持久化模型。
    """


class ImportResult(BaseModel):
    """流水线执行结果。"""

    task: ImportTaskDetail
    chunks: list[Any] = Field(default_factory=list)
    questions: list[Any] = Field(default_factory=list)
    warnings: list[ParserWarning] = Field(default_factory=list)
