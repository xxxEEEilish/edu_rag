"""内容导入解析器。

解析器负责把不同源格式统一转换为 `ParsedDocument` 或 `ParsedQuestionSet`，
后续切片、向量化和入库不需要关心原始格式来自 Markdown、纯文本、DOCX 还是题库
JSON。新增格式时优先注册新的 parser，而不是修改导入服务编排。
"""

from __future__ import annotations

import json
import re
import zipfile
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any
from xml.etree import ElementTree

from schema.import_schema import (
    ImportInputFormat,
    ImportMetadata,
    ParserWarning,
    ParsedDocument,
    ParsedQuestionSet,
    ParsedSection,
    QuestionImportItem,
    stable_sha256,
)


class UnsupportedImportFormatError(ValueError):
    """没有可用解析器时抛出的错误。"""


class ContentParser(ABC):
    """内容解析器抽象基类。"""

    @abstractmethod
    def parse(
        self,
        *,
        file_name: str,
        source_path: str,
        content: bytes,
        metadata: ImportMetadata,
    ) -> ParsedDocument | ParsedQuestionSet:
        """解析原始字节内容并返回统一中间结构。"""


class ParserRegistry:
    """解析器注册表。

    服务层通过注册表选择解析器，避免在导入编排中出现大量文件扩展名判断。后续支持
    PDF、PPT、字幕或 OCR 时，只需新增解析器并注册对应格式。
    """

    def __init__(self) -> None:
        self._parsers: dict[ImportInputFormat, ContentParser] = {}

    def register(self, input_format: ImportInputFormat, parser: ContentParser) -> None:
        self._parsers[input_format] = parser

    def get(self, input_format: ImportInputFormat) -> ContentParser:
        parser = self._parsers.get(input_format)
        if parser is None:
            raise UnsupportedImportFormatError(f"不支持的导入格式: {input_format}")
        return parser


class TextDocumentParser(ContentParser):
    """纯文本和 Markdown 解析器。

    Markdown 标题会被转换为 heading_path；纯文本按空行分段。解析结果保留原始顺序，
    让切片器可以按文档流生成稳定片段。
    """

    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

    def __init__(self, *, markdown: bool = False) -> None:
        self.markdown = markdown

    def parse(
        self,
        *,
        file_name: str,
        source_path: str,
        content: bytes,
        metadata: ImportMetadata,
    ) -> ParsedDocument:
        text = content.decode("utf-8")
        warnings: list[ParserWarning] = []
        sections: list[ParsedSection] = []
        heading_stack: list[str] = []
        buffer: list[str] = []
        order = 0

        def flush(location: str) -> None:
            nonlocal order
            joined = "\n".join(line.strip() for line in buffer if line.strip()).strip()
            buffer.clear()
            if not joined:
                return
            order += 1
            sections.append(
                ParsedSection(
                    text=joined,
                    heading_path=list(heading_stack),
                    order=order,
                    source_file_name=file_name,
                    source_path=source_path,
                    location=location,
                    metadata=metadata,
                )
            )

        for line_number, line in enumerate(text.splitlines(), start=1):
            heading_match = self.heading_pattern.match(line.strip()) if self.markdown else None
            if heading_match:
                flush(f"line:{line_number}")
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                heading_stack = heading_stack[: level - 1] + [title]
                continue
            if not line.strip():
                flush(f"line:{line_number}")
                continue
            buffer.append(line)
        flush("eof")

        if not sections:
            warnings.append(ParserWarning(code="empty_document", message="文档未解析出可导入文本"))

        return ParsedDocument(
            file_name=file_name,
            source_path=source_path,
            source_hash=stable_sha256(content),
            sections=sections,
            warnings=warnings,
        )


class DocxDocumentParser(ContentParser):
    """DOCX 解析器。

    首期使用标准库读取 DOCX 的 `word/document.xml`，提取段落和表格文本。该实现不依赖
    外部包，适合当前轻量项目；复杂图片、公式和样式会记录告警，后续可替换为更强的
    python-docx 或文档解析服务。
    """

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    def parse(
        self,
        *,
        file_name: str,
        source_path: str,
        content: bytes,
        metadata: ImportMetadata,
    ) -> ParsedDocument:
        sections: list[ParsedSection] = []
        warnings: list[ParserWarning] = []
        heading_stack: list[str] = []

        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                xml_bytes = archive.read("word/document.xml")
        except Exception as exc:
            raise ValueError(f"DOCX 文件无法读取: {exc}") from exc

        root = ElementTree.fromstring(xml_bytes)
        body = root.find("w:body", self.namespace)
        if body is None:
            warnings.append(ParserWarning(code="empty_docx_body", message="DOCX 缺少正文内容"))
            body_children: list[ElementTree.Element] = []
        else:
            body_children = list(body)

        order = 0
        for element in body_children:
            tag = self._strip_namespace(element.tag)
            if tag == "p":
                text = self._paragraph_text(element)
                if not text:
                    continue
                style = self._paragraph_style(element)
                if style and style.lower().startswith("heading"):
                    level = self._heading_level(style)
                    heading_stack = heading_stack[: level - 1] + [text]
                    continue
                order += 1
                sections.append(
                    ParsedSection(
                        text=text,
                        heading_path=list(heading_stack),
                        order=order,
                        source_file_name=file_name,
                        source_path=source_path,
                        location=f"paragraph:{order}",
                        metadata=metadata,
                    )
                )
            elif tag == "tbl":
                table_text = self._table_text(element)
                if table_text:
                    order += 1
                    sections.append(
                        ParsedSection(
                            text=table_text,
                            heading_path=list(heading_stack),
                            order=order,
                            source_file_name=file_name,
                            source_path=source_path,
                            location=f"table:{order}",
                            metadata=metadata,
                        )
                    )

        if root.findall(".//w:drawing", self.namespace):
            warnings.append(
                ParserWarning(
                    code="unsupported_docx_drawing",
                    message="DOCX 包含图片或绘图对象，首期仅记录占位告警，不提取图像内容",
                )
            )
        if root.findall(".//m:oMath", {"m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}):
            warnings.append(
                ParserWarning(
                    code="unsupported_docx_formula",
                    message="DOCX 包含公式对象，首期仅记录告警，不转换公式内容",
                )
            )
        if not sections:
            warnings.append(ParserWarning(code="empty_document", message="DOCX 未解析出可导入文本"))

        return ParsedDocument(
            file_name=file_name,
            source_path=source_path,
            source_hash=stable_sha256(content),
            sections=sections,
            warnings=warnings,
        )

    def _strip_namespace(self, tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def _paragraph_text(self, paragraph: ElementTree.Element) -> str:
        texts = [node.text or "" for node in paragraph.findall(".//w:t", self.namespace)]
        return "".join(texts).strip()

    def _paragraph_style(self, paragraph: ElementTree.Element) -> str | None:
        style = paragraph.find(".//w:pStyle", self.namespace)
        if style is None:
            return None
        return style.attrib.get(f"{{{self.namespace['w']}}}val")

    def _heading_level(self, style: str) -> int:
        match = re.search(r"(\d+)$", style)
        return int(match.group(1)) if match else 1

    def _table_text(self, table: ElementTree.Element) -> str:
        rows: list[str] = []
        for row in table.findall(".//w:tr", self.namespace):
            cells = []
            for cell in row.findall("./w:tc", self.namespace):
                cell_text = " ".join(
                    text.text or "" for text in cell.findall(".//w:t", self.namespace)
                ).strip()
                cells.append(cell_text)
            if any(cells):
                rows.append(" | ".join(cells))
        return "\n".join(rows).strip()


class QuestionJsonParser(ContentParser):
    """结构化题库 JSON 解析器。

    支持顶层数组，或包含 `questions` 数组的对象。每道题会继承导入请求中的课程、章节、
    租户等元数据，同时可覆盖题库名称、难度、选项和解析等字段。
    """

    def parse(
        self,
        *,
        file_name: str,
        source_path: str,
        content: bytes,
        metadata: ImportMetadata,
    ) -> ParsedQuestionSet:
        raw = json.loads(content.decode("utf-8"))
        records = raw.get("questions", raw) if isinstance(raw, dict) else raw
        if not isinstance(records, list):
            raise ValueError("题库 JSON 必须是数组，或包含 questions 数组字段")

        questions: list[QuestionImportItem] = []
        warnings: list[ParserWarning] = []
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                warnings.append(
                    ParserWarning(
                        code="invalid_question_record",
                        message="题目记录必须是对象",
                        location=f"question:{index}",
                    )
                )
                continue
            merged = self._normalize_record(record, file_name, source_path, metadata)
            try:
                questions.append(QuestionImportItem(**merged))
            except Exception as exc:
                warnings.append(
                    ParserWarning(
                        code="invalid_question_record",
                        message=str(exc),
                        location=f"question:{index}",
                    )
                )

        if not questions:
            raise ValueError("题库未解析出有效题目")

        return ParsedQuestionSet(
            file_name=file_name,
            source_path=source_path,
            source_hash=stable_sha256(content),
            questions=questions,
            warnings=warnings,
        )

    def _normalize_record(
        self,
        record: dict[str, Any],
        file_name: str,
        source_path: str,
        metadata: ImportMetadata,
    ) -> dict[str, Any]:
        """补齐题目来源字段并生成内容哈希。"""
        content_seed = json.dumps(record, ensure_ascii=False, sort_keys=True)
        return {
            **record,
            "source_file_name": record.get("source_file_name") or file_name,
            "source_path": record.get("source_path") or source_path,
            "content_hash": record.get("content_hash") or stable_sha256(content_seed),
            "metadata": metadata,
        }


def default_parser_registry() -> ParserRegistry:
    """创建首期默认解析器注册表。"""
    registry = ParserRegistry()
    registry.register(ImportInputFormat.TEXT, TextDocumentParser(markdown=False))
    registry.register(ImportInputFormat.MARKDOWN, TextDocumentParser(markdown=True))
    registry.register(ImportInputFormat.DOCX, DocxDocumentParser())
    registry.register(ImportInputFormat.QUESTION_JSON, QuestionJsonParser())
    return registry
