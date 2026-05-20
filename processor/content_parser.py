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
        """注册指定格式的解析器。

        注册表允许后续按配置替换解析器，例如把当前标准库 DOCX 解析器替换为
        python-docx、LibreOffice 转换服务或 OCR 管线。调用方不应绕过注册表直接
        判断扩展名，否则会让格式扩展散落到多个模块。
        """
        self._parsers[input_format] = parser

    def get(self, input_format: ImportInputFormat) -> ContentParser:
        """获取格式对应的解析器。

        如果格式未注册，抛出业务可识别的错误，让导入服务把任务标记为 failed，而不是
        返回空解析结果。空结果会让用户误以为文件成功导入但没有内容。
        """
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
        # heading_stack 保存当前段落所在的标题路径。Markdown 标题层级会动态覆盖栈中
        # 对应层级，保证 “一级标题 / 二级标题 / 正文段落” 的关系能够进入片段元数据。
        heading_stack: list[str] = []
        # buffer 暂存连续正文行，遇到空行或新标题时 flush 成一个 ParsedSection。
        # 这样可以保留自然段边界，避免每一行都变成过短片段。
        buffer: list[str] = []
        order = 0

        def flush(location: str) -> None:
            """把当前缓冲区转换成解析段落。

            location 记录触发 flush 的位置，后续如果用户质疑某个片段来源，可以结合
            source_path、heading_path 和 location 回到原始文档附近进行复核。
            """
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
                # 标题本身不作为正文段落入库，而是作为后续正文的层级上下文。这样召回
                # 结果既能包含正文内容，也能知道正文属于哪个章节。
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
                # DOCX 本质是 zip 包，正文 XML 位于 word/document.xml。当前实现只读取
                # 正文 XML，后续若要提取图片或样式，可继续读取 word/media 和样式表。
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
                    # Word 标题样式用于构造 heading_path，不直接写入正文段落。复杂模板中
                    # 标题样式名称可能不规范，后续可在这里扩展样式映射规则。
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
                # 表格经常承载课程大纲、步骤、题目选项等关键信息。首期把每行拼成
                # “单元格 | 单元格” 的可检索文本，保留顺序优先于保留复杂排版。
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
            # 图片、绘图对象目前不进入文本索引，但必须记录告警。后续多模态导入可以用
            # 这些 warning 作为发现未处理资源的入口。
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
        # 兼容两种常见题库 JSON：直接传数组，或传 {"questions": [...]}。这能降低
        # 初期数据接入成本，同时仍保持每道题的字段校验。
        records = raw.get("questions", raw) if isinstance(raw, dict) else raw
        if not isinstance(records, list):
            raise ValueError("题库 JSON 必须是数组，或包含 questions 数组字段")

        questions: list[QuestionImportItem] = []
        warnings: list[ParserWarning] = []
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                # 非对象记录无法映射为 QuestionImportItem，但不立即中断整个文件，避免
                # 单条脏数据掩盖后续更多有效题目和校验信息。
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
        # 题目内容哈希基于规范化 JSON，而不是原始文件字节。这样同一题即使字段顺序
        # 不同，也能得到相同 hash，便于后续题库增量更新和重复检测。
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
