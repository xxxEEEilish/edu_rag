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
    """内容导入流水线服务。

    该服务是导入能力的唯一编排入口：API 层只负责把 HTTP 请求转换成
    `ImportRequest`，具体的任务创建、状态推进、原始文件保存、解析、切片、
    向量化和元数据落库都在这里完成。这样做的好处是后续即使把同步执行替换为
    Celery、RQ 或独立 worker，核心业务状态机仍然可以复用。

    服务只依赖 `utils.import_adapters` 中定义的协议，不依赖具体基础设施客户端。
    这条边界非常重要：测试可以注入内存适配器，生产环境可以注入 MongoDB、MinIO、
    Milvus 和真实 Embedding 客户端，而导入流程本身不需要知道底层实现。
    """

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
        # 任务仓储负责保存任务状态机的每一次变化。导入链路出现失败时，用户能否看到
        # “失败在哪个阶段”完全依赖这里的状态被及时更新。
        self.task_repository = task_repository
        # 原始文件存储位于解析之前，目的是保证即使后续解析或向量化失败，也能保留
        # 可复核的原始输入，便于重试、人工排查或后续增量导入。
        self.source_store = source_store
        # 文档片段仓储保存可检索文本的业务元数据，不保存真实向量；向量写入由
        # vector_index 处理，二者分离可以避免 MongoDB/Milvus 互相泄漏实现细节。
        self.chunk_repository = chunk_repository
        # 题库数据和文档片段结构差异较大，因此题目单独进入 question_repository，
        # 但仍共享同一任务状态和来源追踪策略。
        self.question_repository = question_repository
        self.embedding_model = embedding_model
        self.vector_index = vector_index
        # parser_registry 和 chunker 支持注入，测试可以替换为特殊失败实现，后续也可以
        # 按租户、文件类型或配置切换更复杂的解析/切片策略。
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
        """执行导入流水线并返回结果。

        状态推进顺序必须保持稳定：重复导入检测 -> 保存原始文件 -> 解析 -> 文档切片或
        题库转换 -> 向量化 -> 向量索引 -> 元数据保存 -> 完成。每个阶段都会更新任务，
        因此即使中途失败，调用方也能通过任务详情看到最后一个阶段和错误原因。
        """
        task = self._require_task(task_id)
        source_bytes = request.source_bytes()
        try:
            # 幂等判断放在原始文件保存之前，避免同一租户重复提交同一来源时浪费存储、
            # 解析和向量化资源。force_reimport 会绕过该逻辑，用于显式重建版本。
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
            # 解析器只返回统一中间结构，不直接产生 KnowledgeChunk 或 Question。
            # 这样文档解析、题库解析和未来 PDF/OCR 解析可以独立演进。
            parser = self.parser_registry.get(request.resolved_format())
            parsed = parser.parse(
                file_name=request.file_name,
                source_path=request.source_path or task.source_path or request.file_name,
                content=source_bytes,
                metadata=request.metadata,
            )
            task.warning_count = len(parsed.warnings)
            task.warnings = parsed.warnings
            # 解析告警是非致命信息，例如 DOCX 图片或公式暂时无法提取。它们需要保存给
            # 管理端展示，但不能阻塞可解析文本继续进入知识库。
            self.chunk_repository.save_parser_warnings(task.task_id, parsed.warnings)
            self._save_task(task)

            # 题库和文档共享同一导入任务生命周期，但落库目标不同：题库保存为结构化
            # Question，文档先切片再进入 Embedding 和向量索引。
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
        """保存文档类导入结果。

        文档类数据需要先生成可检索片段，再为每个片段生成向量。这里故意先完成全部
        Embedding，再批量写向量索引，避免只写入一部分向量却把任务标记为成功。
        """
        self._set_processing(task, ImportStage.CHUNKED, 50, "正在生成知识片段")
        chunks = self.chunker.chunk_document(parsed, task_id=task.task_id, version=task.version)
        task.chunk_count = len(chunks)
        task.imported_chunk_ids = [chunk.chunk_id for chunk in chunks]
        self._save_task(task)

        self._set_processing(task, ImportStage.EMBEDDED, 70, "正在生成文本向量")
        vectors = self.embedding_model.embed_texts([chunk.content for chunk in chunks])
        # Embedding 结果必须与输入片段一一对应；数量不一致通常代表模型服务、适配器或
        # 批处理逻辑异常，继续写入会导致 chunk_id 与向量错位，因此必须失败。
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
        """保存结构化题库导入结果。

        题库数据不进入文档切片器，因为题干、选项、答案和解析需要保持结构化字段，
        方便后续按题型、难度、知识点过滤，也能在问答中精确引用标准答案。
        """
        self._set_processing(task, ImportStage.PERSISTED, 80, "正在保存题库记录")
        questions = [
            Question(
                # 如果上游没有提供题目 ID，则使用题干和任务 ID 生成稳定但任务内唯一的 ID。
                # 真实生产环境后续可以替换为题库系统 ID 或数据库生成 ID。
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
        """把重复导入任务标记为已跳过但成功完成。

        重复导入不是错误：用户提交了已经完成的同源内容，系统应返回一个可查询的任务，
        并指向已有导入结果。这样前端不需要特殊处理“重复”异常，也不会生成重复索引。
        """
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
        """将任务标记为失败并保存错误原因。

        失败处理必须集中在这里，确保所有异常路径都能留下相同结构的状态记录。当前
        `error` 保存用户可读文本；后续如果需要内部错误码、堆栈或重试策略，可以在
        ImportTask 中扩展字段，而不改变 API 的基本状态语义。
        """
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
