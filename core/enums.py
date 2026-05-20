"""全局枚举定义。

枚举值是 API、Schema、存储和检索流程之间的公共语言。集中定义可以避免
不同模块手写字符串造成拼写不一致，也方便后续新增视频、多模态等内容类型。
"""

from enum import StrEnum


class ContentType(StrEnum):
    """知识库内容类型。

    该枚举同时覆盖一期文档/题目/课程内容和后续视频、图片扩展点。
    """

    COURSE = "course"
    DOCUMENT = "document"
    DOCUMENT_CHUNK = "document_chunk"
    QUESTION = "question"
    PROJECT = "project"
    VIDEO = "video"
    IMAGE = "image"


class ImportTaskStatus(StrEnum):
    """导入任务生命周期状态。

    后续上传、解析、切片、向量化和入库阶段都会围绕这些状态更新任务记录。
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class QueryIntent(StrEnum):
    """用户查询意图。

    检索问答阶段会先识别意图，再选择课程、文档、题库、项目或视频等召回路径。
    """

    COURSE_INTRO = "course_intro"
    COURSE_DETAIL = "course_detail"
    DOCUMENT_SEARCH = "document_search"
    QUESTION_SEARCH = "question_search"
    PROJECT_QA = "project_qa"
    VIDEO_SEARCH = "video_search"
    GENERAL_QA = "general_qa"


class SourceType(StrEnum):
    """答案引用来源类型。

    用于让查询响应明确说明答案来自课程、章节、文档、题目、项目或视频片段。
    """

    COURSE = "course"
    CHAPTER = "chapter"
    DOCUMENT = "document"
    QUESTION = "question"
    PROJECT = "project"
    VIDEO_SEGMENT = "video_segment"
    IMAGE = "image"
