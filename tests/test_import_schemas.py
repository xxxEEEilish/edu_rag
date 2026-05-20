"""内容导入 Schema 测试。

这些测试锁定 API 请求、任务详情、解析告警和中间解析结构，避免后续实现阶段破坏
导入流水线各层之间的数据契约。
"""

import pytest

from schema.import_schema import (
    ImportInputFormat,
    ImportMetadata,
    ImportRequest,
    ImportTask,
    ParsedSection,
    ParserWarning,
    stable_sha256,
)


def test_import_request_defaults_source_path_and_format() -> None:
    """请求模型应能补齐来源路径，并从文件名推断解析格式。"""
    request = ImportRequest(
        file_name="lesson.md",
        source_text="# Title",
        metadata=ImportMetadata(course_name="Python Intro"),
    )

    assert request.source_path == "raw/default/lesson.md"
    assert request.resolved_format() == ImportInputFormat.MARKDOWN
    assert request.source_bytes() == b"# Title"


def test_import_request_requires_source_text() -> None:
    """首期 JSON 导入必须携带 source_text。"""
    with pytest.raises(ValueError):
        ImportRequest(
            file_name="lesson.txt",
            metadata=ImportMetadata(course_name="Python Intro"),
        )


def test_import_task_from_request_preserves_metadata() -> None:
    """任务记录应继承请求中的租户、课程、章节和哈希字段。"""
    request = ImportRequest(
        file_name="lesson.txt",
        source_text="content",
        metadata=ImportMetadata(
            tenant_id="school_a",
            course_name="Python Intro",
            chapter_name="Functions",
        ),
    )
    task = ImportTask.from_request(request, source_hash=stable_sha256(request.source_bytes()))

    assert task.tenant_id == "school_a"
    assert task.course_name == "Python Intro"
    assert task.chapter_name == "Functions"
    assert task.progress == 0
    assert task.source_hash == stable_sha256(b"content")


def test_parser_warning_and_parsed_section_models() -> None:
    """解析告警和段落模型应保留位置、标题路径和来源元数据。"""
    metadata = ImportMetadata(course_name="Python Intro")
    warning = ParserWarning(code="unsupported_image", message="skip image", location="p:1")
    section = ParsedSection(
        text="Functions use def.",
        heading_path=["Python", "Functions"],
        order=1,
        source_file_name="lesson.md",
        source_path="raw/default/lesson.md",
        metadata=metadata,
    )

    assert warning.location == "p:1"
    assert section.heading_path == ["Python", "Functions"]
    assert section.metadata.course_name == "Python Intro"
