"""内容导入流水线的内存适配器。

这些实现用于单元测试和本地离线试运行。它们遵守真实适配器协议，但不会连接任何
外部服务，因此不会破坏应用启动和测试的离线约束。
"""

from copy import deepcopy

from schema.chunk_schema import KnowledgeChunk
from schema.import_schema import ImportTask, ParserWarning
from schema.question_schema import Question


class InMemoryImportTaskRepository:
    """以内存字典保存导入任务状态。"""

    def __init__(self) -> None:
        self.tasks: dict[str, ImportTask] = {}

    def create_task(self, task: ImportTask) -> ImportTask:
        self.tasks[task.task_id] = deepcopy(task)
        return deepcopy(task)

    def update_task(self, task: ImportTask) -> ImportTask:
        self.tasks[task.task_id] = deepcopy(task)
        return deepcopy(task)

    def get_task(self, task_id: str) -> ImportTask | None:
        task = self.tasks.get(task_id)
        return deepcopy(task) if task else None

    def find_completed_by_source(
        self,
        *,
        tenant_id: str,
        source_path: str,
        source_hash: str,
    ) -> ImportTask | None:
        for task in self.tasks.values():
            if (
                task.tenant_id == tenant_id
                and task.source_path == source_path
                and task.source_hash == source_hash
                and task.status == "completed"
            ):
                return deepcopy(task)
        return None


class InMemorySourceObjectStore:
    """以内存字典保存原始导入内容。"""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.objects: dict[str, bytes] = {}

    def save_source(
        self,
        *,
        tenant_id: str,
        task_id: str,
        file_name: str,
        content: bytes,
    ) -> str:
        if self.fail:
            raise RuntimeError("对象存储不可用")
        path = f"memory://{tenant_id}/{task_id}/{file_name}"
        self.objects[path] = content
        return path


class InMemoryChunkRepository:
    """以内存列表保存片段元数据和解析告警。"""

    def __init__(self) -> None:
        self.chunks: list[KnowledgeChunk] = []
        self.warnings: dict[str, list[ParserWarning]] = {}

    def save_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        self.chunks.extend(deepcopy(chunks))

    def save_parser_warnings(self, task_id: str, warnings: list[ParserWarning]) -> None:
        self.warnings[task_id] = deepcopy(warnings)


class InMemoryQuestionRepository:
    """以内存列表保存题目记录。"""

    def __init__(self) -> None:
        self.questions: list[Question] = []

    def save_questions(self, questions: list[Question]) -> None:
        self.questions.extend(deepcopy(questions))


class InMemoryVectorIndex:
    """以内存列表记录向量写入调用。"""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.records: list[tuple[str, list[float]]] = []

    def upsert_vectors(
        self,
        *,
        vectors: list[list[float]],
        chunks: list[KnowledgeChunk],
    ) -> None:
        if self.fail:
            raise RuntimeError("向量索引不可用")
        self.records.extend((chunk.chunk_id, vector) for chunk, vector in zip(chunks, vectors))


class DeterministicEmbeddingModel:
    """为测试提供稳定向量的 Embedding 替身。

    向量值只和文本长度及序号有关，既能验证调用数量，也能避免测试依赖真实模型服务。
    """

    def __init__(self, *, dim: int = 4, mismatch: bool = False) -> None:
        self.dim = dim
        self.mismatch = mismatch
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        count = max(0, len(texts) - 1) if self.mismatch else len(texts)
        return [[float(len(texts[index]) + offset) for offset in range(self.dim)] for index in range(count)]
