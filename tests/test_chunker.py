"""知识切片器测试。"""

from processor.chunker import ChunkerConfig, DocumentChunker
from schema.import_schema import ImportMetadata, ParsedDocument, ParsedSection, stable_sha256


def test_chunker_applies_size_overlap_and_metadata() -> None:
    """切片器应按窗口切片，并传播来源、课程、章节和知识点字段。"""
    metadata = ImportMetadata(
        tenant_id="school_a",
        course_name="Python Intro",
        chapter_name="Functions",
        knowledge_points=["function"],
    )
    section = ParsedSection(
        text="abcdefghij",
        heading_path=["Python"],
        order=1,
        source_file_name="lesson.md",
        source_path="raw/school_a/lesson.md",
        metadata=metadata,
    )
    document = ParsedDocument(
        file_name="lesson.md",
        source_path="raw/school_a/lesson.md",
        source_hash=stable_sha256("abcdefghij"),
        sections=[section],
    )

    chunks = DocumentChunker(ChunkerConfig(chunk_size=8, chunk_overlap=2)).chunk_document(
        document,
        task_id="task_001",
    )

    assert len(chunks) >= 2
    assert chunks[0].course_name == "Python Intro"
    assert chunks[0].chapter_name == "Functions"
    assert chunks[0].tenant_id == "school_a"
    assert chunks[0].source_file_name == "lesson.md"
    assert chunks[0].content_hash
    assert chunks[0].chunk_id.startswith("chunk_")
