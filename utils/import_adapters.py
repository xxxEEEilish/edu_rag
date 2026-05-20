"""内容导入流水线适配器契约。

服务层只依赖这些协议，不直接依赖 MongoDB、MinIO、Milvus 或具体 Embedding
客户端。这样可以在单元测试中注入内存实现，也能在生产环境中把协议映射到真实
基础设施客户端。
"""

from typing import Protocol

from schema.chunk_schema import KnowledgeChunk
from schema.import_schema import ImportTask, ParserWarning
from schema.question_schema import Question


class ImportTaskRepository(Protocol):
    """导入任务元数据仓储协议。"""

    def create_task(self, task: ImportTask) -> ImportTask:
        """保存新任务并返回保存后的任务对象。"""

    def update_task(self, task: ImportTask) -> ImportTask:
        """覆盖更新任务状态、进度、错误和统计字段。"""

    def get_task(self, task_id: str) -> ImportTask | None:
        """根据任务 ID 获取任务，找不到时返回 None。"""

    def find_completed_by_source(
        self,
        *,
        tenant_id: str,
        source_path: str,
        source_hash: str,
    ) -> ImportTask | None:
        """查找同租户、同来源、同源哈希的已完成导入任务，用于幂等判断。"""


class SourceObjectStore(Protocol):
    """原始导入文件对象存储协议。"""

    def save_source(
        self,
        *,
        tenant_id: str,
        task_id: str,
        file_name: str,
        content: bytes,
    ) -> str:
        """保存原始文件并返回可追踪的存储路径。"""


class ChunkMetadataRepository(Protocol):
    """知识片段和解析告警元数据仓储协议。"""

    def save_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        """批量保存知识片段元数据。"""

    def save_parser_warnings(self, task_id: str, warnings: list[ParserWarning]) -> None:
        """保存解析告警，便于状态页和后台管理查看。"""


class QuestionRepository(Protocol):
    """题库元数据仓储协议。"""

    def save_questions(self, questions: list[Question]) -> None:
        """批量保存题目记录。"""


class VectorIndex(Protocol):
    """向量索引写入协议。"""

    def upsert_vectors(
        self,
        *,
        vectors: list[list[float]],
        chunks: list[KnowledgeChunk],
    ) -> None:
        """将向量和对应片段标识写入向量索引。"""


class TextEmbeddingModel(Protocol):
    """文本向量化协议。"""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """按输入顺序返回同数量文本向量。"""
