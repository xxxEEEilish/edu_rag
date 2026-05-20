"""知识片段切片器。

切片器接收解析后的有序段落，生成可写入元数据仓储和向量索引的 `KnowledgeChunk`。
它负责控制片段大小、重叠窗口、稳定 ID、内容哈希和来源字段传播。
"""

from dataclasses import dataclass

from core.enums import ContentType
from schema.chunk_schema import KnowledgeChunk
from schema.import_schema import ParsedDocument, ParsedSection, stable_sha256


@dataclass(frozen=True)
class ChunkerConfig:
    """切片配置。

    `chunk_size` 和 `chunk_overlap` 以字符数计，首期实现保持简单可测；后续可替换为
    token-aware 切片器，但仍复用同一输入输出结构。
    """

    chunk_size: int = 800
    chunk_overlap: int = 120

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")


class DocumentChunker:
    """文档切片器。

    切片器只处理 `ParsedDocument`，不关心文档来自 Markdown、DOCX 还是后续 PDF。
    这个边界保证“解析格式扩展”和“切片策略优化”可以独立演进：解析器负责还原文档
    结构，切片器负责把结构化文本变成适合向量检索的片段。
    """

    def __init__(self, config: ChunkerConfig | None = None) -> None:
        self.config = config or ChunkerConfig()

    def chunk_document(self, document: ParsedDocument, *, task_id: str, version: str = "v1") -> list[KnowledgeChunk]:
        """将解析文档转换为知识片段列表。

        `task_id` 当前不参与片段 ID 计算，原因是同一内容在同一租户和来源下应生成稳定
        chunk_id，便于幂等写入和增量对比。保留参数是为了未来需要按任务追踪切片来源时
        不改变调用签名。
        """
        chunks: list[KnowledgeChunk] = []
        for section in document.sections:
            chunks.extend(self._chunk_section(section, task_id=task_id, version=version))
        return chunks

    def _chunk_section(self, section: ParsedSection, *, task_id: str, version: str) -> list[KnowledgeChunk]:
        """对单个解析段落按字符窗口切片。"""
        content = self._section_content(section)
        if not content:
            return []

        chunks: list[KnowledgeChunk] = []
        start = 0
        index = 0
        while start < len(content):
            end = min(len(content), start + self.config.chunk_size)
            text = content[start:end].strip()
            if text:
                index += 1
                # content_hash 基于最终进入向量化的文本计算，而不是原始段落。这样标题
                # 前缀、窗口切分和重叠都会反映在 hash 中，后续排查向量记录时更准确。
                content_hash = stable_sha256(text)
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=self._chunk_id(
                            tenant_id=section.metadata.tenant_id,
                            source_path=section.source_path,
                            section_order=section.order,
                            chunk_index=index,
                            content_hash=content_hash,
                        ),
                        # content 是后续 Embedding 的唯一输入文本。这里已经合并标题路径，
                        # 让向量语义包含章节上下文，减少短段落被单独召回时语义不完整的问题。
                        content=text,
                        content_type=ContentType.DOCUMENT_CHUNK,
                        course_id=section.metadata.course_id,
                        course_name=section.metadata.course_name,
                        chapter_id=section.metadata.chapter_id,
                        chapter_name=section.metadata.chapter_name,
                        project_id=section.metadata.project_id,
                        project_name=section.metadata.project_name,
                        knowledge_points=section.metadata.knowledge_points,
                        source_file_name=section.source_file_name,
                        source_path=section.source_path,
                        version=version,
                        tenant_id=section.metadata.tenant_id,
                        content_hash=content_hash,
                    )
                )
            if end == len(content):
                break
            # 重叠窗口让跨边界的句子或步骤说明能同时出现在相邻片段里。首期按字符重叠，
            # 后续替换为 token-aware 切片时应保留“相邻片段保留上下文”的不变量。
            start = end - self.config.chunk_overlap
        return chunks

    def _section_content(self, section: ParsedSection) -> str:
        """组合标题路径和正文，增强片段独立可读性。"""
        prefix = " / ".join(section.heading_path)
        return f"{prefix}\n{section.text}".strip() if prefix else section.text.strip()

    def _chunk_id(
        self,
        *,
        tenant_id: str,
        source_path: str,
        section_order: int,
        chunk_index: int,
        content_hash: str,
    ) -> str:
        """生成稳定片段 ID。

        ID 同时包含来源、位置和内容哈希，既利于幂等写入，也便于人工排查重复片段。
        """
        seed = f"{tenant_id}|{source_path}|{section_order}|{chunk_index}|{content_hash}"
        return f"chunk_{stable_sha256(seed)[:24]}"
