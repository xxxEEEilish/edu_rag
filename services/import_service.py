"""内容导入服务编排。

服务层把 API 请求、解析器、切片器、Embedding、向量索引和元数据仓储串成稳定状态机。
它不直接连接外部系统，而是依赖适配器协议，因此可以在测试环境中完全离线运行。
"""

from core.enums import ImportTaskStatus
from processor.chunker import DocumentChunker
from processor.content_parser import ParserRegistry, default_parser_registry
from schema.import_schema import (
    ImportRequest,
    ImportResult,
    ImportStage,
    ImportTask,
    ImportTaskDetail,
    ParsedDocument,
    ParsedQuestionSet,
    stable_sha256,
)
from schema.question_schema import Question
from utils.import_adapters import (
    ChunkMetadataRepository,
    ImportTaskRepository,
    QuestionRepository,
    SourceObjectStore,
    TextEmbeddingModel,
    VectorIndex,
)


class ImportTaskNotFoundError(KeyError):
    """查询不存在的导入任务时抛出。"""


class ImportService:
    """内容导入流水线服务。"""

    def __init__(
        self,
        *,
        task_repository: ImportTaskRepository,
        source_store: SourceObjectStore,
        chunk_repository: ChunkMetadataRepository,
        question_repository: QuestionRepository,
        embedding_model: TextEmbeddingModel,
        vector_index: VectorIndex,
        parser_registry: ParserRegistry | None = None,
        chunker: DocumentChunker | None = None,
    ) -> None:
        self.task_repository = task_repository
        self.source_store = source_store
        self.chunk_repository = chunk_repository
        self.question_repository = question_repository
        self.embedding_model = embedding_model
        self.vector_index = vector_index
        self.parser_registry = parser_registry or default_parser_registry()
        self.chunker = chunker or DocumentChunker()

    def create_task(self, request: ImportRequest) -> ImportTaskDetail:
        """创建待处理任务。

        该方法只进行请求校验、哈希计算和初始状态保存，不执行耗时解析，方便后续接入
        后台任务队列或异步 worker。
        """
        source_hash = stable_sha256(request.source_bytes())
        task = ImportTask.from_request(request, source_hash=source_hash)
        created = self.task_repository.create_task(task)
        return ImportTaskDetail(**created.model_dump())

    def submit_and_run(self, request: ImportRequest) -> ImportResult:
        """创建并立即执行导入任务。

        首期 API 和测试使用同步执行，后续如果切换为后台任务，可继续复用 `create_task`
        与 `run_task` 的边界。
        """
        task = self.create_task(request)
        return self.run_task(task.task_id, request)

    def run_task(self, task_id: str, request: ImportRequest) -> ImportResult:
        """执行导入流水线并返回结果。"""
        task = self._require_task(task_id)
        source_bytes = request.source_bytes()
        try:
            duplicate = self._find_duplicate(task, request)
            if duplicate:
                return self._complete_duplicate(task, duplicate)

            self._set_processing(task, ImportStage.STORED_SOURCE, 10, "正在保存原始文件")
            task.stored_source_path = self.source_store.save_source(
                tenant_id=task.tenant_id,
                task_id=task.task_id,
                file_name=task.file_name,
                content=source_bytes,
            )
            self._save_task(task)

            self._set_processing(task, ImportStage.PARSED, 30, "正在解析内容")
            parser = self.parser_registry.get(request.resolved_format())
            parsed = parser.parse(
                file_name=request.file_name,
                source_path=request.source_path or task.source_path or request.file_name,
                content=source_bytes,
                metadata=request.metadata,
            )
            task.warning_count = len(parsed.warnings)
            task.warnings = parsed.warnings
            self.chunk_repository.save_parser_warnings(task.task_id, parsed.warnings)
            self._save_task(task)

            if isinstance(parsed, ParsedQuestionSet):
                return self._persist_questions(task, parsed)
            return self._persist_document(task, parsed)
        except Exception as exc:
            return self._fail_task(task, exc)

    def get_task(self, task_id: str) -> ImportTaskDetail:
        """查询任务详情。"""
        task = self.task_repository.get_task(task_id)
        if task is None:
            raise ImportTaskNotFoundError(task_id)
        return ImportTaskDetail(**task.model_dump())

    def _persist_document(self, task: ImportTask, parsed: ParsedDocument) -> ImportResult:
        """保存文档类导入结果。"""
        self._set_processing(task, ImportStage.CHUNKED, 50, "正在生成知识片段")
        chunks = self.chunker.chunk_document(parsed, task_id=task.task_id, version=task.version)
        task.chunk_count = len(chunks)
        task.imported_chunk_ids = [chunk.chunk_id for chunk in chunks]
        self._save_task(task)

        self._set_processing(task, ImportStage.EMBEDDED, 70, "正在生成文本向量")
        vectors = self.embedding_model.embed_texts([chunk.content for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("Embedding 返回数量与知识片段数量不一致")
        self._save_task(task)

        self._set_processing(task, ImportStage.INDEXED, 85, "正在写入向量索引")
        self.vector_index.upsert_vectors(vectors=vectors, chunks=chunks)
        self._save_task(task)

        self._set_processing(task, ImportStage.PERSISTED, 95, "正在保存片段元数据")
        self.chunk_repository.save_chunks(chunks)
        task.status = ImportTaskStatus.COMPLETED
        task.progress = 100
        task.message = "导入完成"
        task.error = None
        self._save_task(task)
        return ImportResult(
            task=ImportTaskDetail(**task.model_dump()),
            chunks=chunks,
            warnings=parsed.warnings,
        )

    def _persist_questions(self, task: ImportTask, parsed: ParsedQuestionSet) -> ImportResult:
        """保存结构化题库导入结果。"""
        self._set_processing(task, ImportStage.PERSISTED, 80, "正在保存题库记录")
        questions = [
            Question(
                question_id=item.question_id or f"question_{stable_sha256(item.stem + task.task_id)[:24]}",
                question_code=item.question_code,
                question_bank_name=item.question_bank_name,
                question_type=item.question_type,
                stem=item.stem,
                options=item.options,
                answer=item.answer,
                analysis=item.analysis,
                difficulty=item.difficulty,
                course_id=item.metadata.course_id,
                course_name=item.metadata.course_name,
                chapter_id=item.metadata.chapter_id,
                chapter_name=item.metadata.chapter_name,
                knowledge_points=item.metadata.knowledge_points,
                tenant_id=item.metadata.tenant_id,
                source_file_name=item.source_file_name,
                source_path=item.source_path,
                import_task_id=task.task_id,
                content_hash=item.content_hash,
            )
            for item in parsed.questions
        ]
        self.question_repository.save_questions(questions)
        task.question_count = len(questions)
        task.imported_question_ids = [question.question_id for question in questions]
        task.status = ImportTaskStatus.COMPLETED
        task.progress = 100
        task.message = "题库导入完成"
        task.error = None
        self._save_task(task)
        return ImportResult(
            task=ImportTaskDetail(**task.model_dump()),
            questions=questions,
            warnings=parsed.warnings,
        )

    def _find_duplicate(self, task: ImportTask, request: ImportRequest) -> ImportTask | None:
        """根据租户、来源路径和源哈希查找重复导入。"""
        if request.force_reimport or not task.source_path or not task.source_hash:
            return None
        return self.task_repository.find_completed_by_source(
            tenant_id=task.tenant_id,
            source_path=task.source_path,
            source_hash=task.source_hash,
        )

    def _complete_duplicate(self, task: ImportTask, duplicate: ImportTask) -> ImportResult:
        """把重复导入任务标记为已跳过但成功完成。"""
        task.status = ImportTaskStatus.COMPLETED
        task.stage = ImportStage.SKIPPED_DUPLICATE
        task.progress = 100
        task.duplicate_of_task_id = duplicate.task_id
        task.message = "检测到重复来源，已跳过重复入库"
        task.chunk_count = duplicate.chunk_count
        task.question_count = duplicate.question_count
        task.imported_chunk_ids = list(duplicate.imported_chunk_ids)
        task.imported_question_ids = list(duplicate.imported_question_ids)
        self._save_task(task)
        return ImportResult(task=ImportTaskDetail(**task.model_dump()))

    def _set_processing(
        self,
        task: ImportTask,
        stage: ImportStage,
        progress: int,
        message: str,
    ) -> None:
        """更新任务为处理中状态。"""
        task.status = ImportTaskStatus.PROCESSING
        task.stage = stage
        task.progress = progress
        task.message = message
        task.error = None

    def _fail_task(self, task: ImportTask, exc: Exception) -> ImportResult:
        """将任务标记为失败并保存错误原因。"""
        task.status = ImportTaskStatus.FAILED
        task.stage = ImportStage.FAILED
        task.message = "导入失败"
        task.error = str(exc)
        self._save_task(task)
        return ImportResult(task=ImportTaskDetail(**task.model_dump()))

    def _save_task(self, task: ImportTask) -> ImportTask:
        """刷新时间戳并保存任务。"""
        task.touch()
        return self.task_repository.update_task(task)

    def _require_task(self, task_id: str) -> ImportTask:
        task = self.task_repository.get_task(task_id)
        if task is None:
            raise ImportTaskNotFoundError(task_id)
        return task
