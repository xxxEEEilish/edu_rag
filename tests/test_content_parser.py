"""内容解析器测试。"""

import json
import zipfile
from io import BytesIO

from processor.content_parser import (
    DocxDocumentParser,
    QuestionJsonParser,
    TextDocumentParser,
    default_parser_registry,
)
from schema.import_schema import ImportInputFormat, ImportMetadata


def test_parser_registry_selects_registered_parser() -> None:
    """默认注册表应能按格式返回对应解析器。"""
    registry = default_parser_registry()

    assert isinstance(registry.get(ImportInputFormat.MARKDOWN), TextDocumentParser)
    assert isinstance(registry.get(ImportInputFormat.DOCX), DocxDocumentParser)


def test_markdown_parser_preserves_heading_path() -> None:
    """Markdown 标题应传播到解析段落的 heading_path。"""
    parser = TextDocumentParser(markdown=True)
    document = parser.parse(
        file_name="lesson.md",
        source_path="raw/default/lesson.md",
        content="# Python\n\n## Functions\n\nUse def.".encode("utf-8"),
        metadata=ImportMetadata(course_name="Python Intro"),
    )

    assert len(document.sections) == 1
    assert document.sections[0].heading_path == ["Python", "Functions"]
    assert document.sections[0].text == "Use def."


def test_plain_text_parser_splits_by_blank_lines() -> None:
    """纯文本解析器应按空行保留自然段顺序。"""
    parser = TextDocumentParser()
    document = parser.parse(
        file_name="lesson.txt",
        source_path="raw/default/lesson.txt",
        content="First paragraph.\n\nSecond paragraph.".encode("utf-8"),
        metadata=ImportMetadata(course_name="Python Intro"),
    )

    assert [section.text for section in document.sections] == [
        "First paragraph.",
        "Second paragraph.",
    ]


def test_docx_parser_extracts_paragraph_and_table_text() -> None:
    """DOCX 解析器应从 document.xml 提取段落和表格文本。"""
    xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Python</w:t></w:r></w:p>
        <w:p><w:r><w:t>Functions use def.</w:t></w:r></w:p>
        <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Name</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Value</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
      </w:body>
    </w:document>
    """
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", xml)

    document = DocxDocumentParser().parse(
        file_name="lesson.docx",
        source_path="raw/default/lesson.docx",
        content=buffer.getvalue(),
        metadata=ImportMetadata(course_name="Python Intro"),
    )

    assert document.sections[0].heading_path == ["Python"]
    assert document.sections[0].text == "Functions use def."
    assert document.sections[1].text == "Name | Value"


def test_question_json_parser_validates_records() -> None:
    """题库 JSON 解析器应生成带来源和内容哈希的题目导入项。"""
    payload = {
        "questions": [
            {
                "question_type": "single_choice",
                "stem": "Which keyword defines a function?",
                "options": ["func", "def"],
                "answer": "def",
            }
        ]
    }

    parsed = QuestionJsonParser().parse(
        file_name="questions.json",
        source_path="raw/default/questions.json",
        content=json.dumps(payload).encode("utf-8"),
        metadata=ImportMetadata(course_name="Python Intro"),
    )

    assert len(parsed.questions) == 1
    assert parsed.questions[0].source_file_name == "questions.json"
    assert parsed.questions[0].content_hash
