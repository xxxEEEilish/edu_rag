"""查询请求与响应 Schema。

这些模型定义聊天问答接口的边界。后续检索、RAG 生成、SSE 和历史记录都应
围绕这些字段扩展，避免 API 响应格式频繁变化。
"""

from pydantic import BaseModel, Field

from core.enums import QueryIntent
from schema.chunk_schema import ReferenceSource


class QueryRequest(BaseModel):
    """用户查询请求。

    `metadata_filter` 预留给课程、章节、题型、难度等过滤条件；当前只定义
    数据结构，实际过滤生成和检索逻辑在后续查询链路实现。
    """

    query: str
    session_id: str | None = None
    is_stream: bool = False
    course_id: str | None = None
    course_name: str | None = None
    tenant_id: str = "default"
    metadata_filter: dict[str, str | int | float | bool] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    """查询响应。

    `references` 保存可追溯来源，`metadata` 保存耗时、模型、召回数量等扩展
    信息，便于后续调试和前端展示。
    """

    message: str = "processed"
    session_id: str | None = None
    intent: QueryIntent = QueryIntent.GENERAL_QA
    answer: str
    references: list[ReferenceSource] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
