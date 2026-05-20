"""核心 Schema 测试。

这些测试锁定导入、索引和查询链路会复用的数据契约，防止后续字段调整破坏
来源追溯、题目结构或查询响应格式。
"""

from core.enums import ContentType, QueryIntent, SourceType
from schema.chunk_schema import KnowledgeChunk, ReferenceSource
from schema.import_schema import ImportTask
from schema.query_schema import QueryRequest, QueryResponse
from schema.question_schema import Question


def test_knowledge_chunk_traceability_fields() -> None:
    """知识片段必须保留来源、租户、版本和启用状态等追溯字段。"""
    chunk = KnowledgeChunk(
        chunk_id="chunk_001",
        content="Python function basics",
        course_name="Python Intro",
        chapter_name="Functions",
        source_file_name="functions.md",
        source_path="raw/default/python/functions.md",
        content_hash="abc123",
    )

    assert chunk.content_type == ContentType.DOCUMENT_CHUNK
    assert chunk.tenant_id == "default"
    assert chunk.version == "v1"
    assert chunk.is_active is True
    assert chunk.source_file_name == "functions.md"


def test_question_import_and_query_schemas() -> None:
    """题目、导入任务、查询请求和查询响应应能组合出一期最小数据流。"""
    question = Question(
        question_id="q_001",
        question_type="single_choice",
        stem="Which keyword defines a Python function?",
        options=["func", "def"],
        answer="def",
    )
    task = ImportTask(task_id="task_001", file_name="questions.csv")
    request = QueryRequest(query="How do I define a Python function?")
    reference = ReferenceSource(
        source_type=SourceType.DOCUMENT,
        content_type=ContentType.DOCUMENT_CHUNK,
        source_file_name="functions.md",
    )
    response = QueryResponse(
        answer="Use def.",
        intent=QueryIntent.GENERAL_QA,
        references=[reference],
    )

    assert question.options == ["func", "def"]
    assert task.progress == 0
    assert request.tenant_id == "default"
    assert response.references[0].source_file_name == "functions.md"
