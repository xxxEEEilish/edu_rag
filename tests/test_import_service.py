"""内容导入服务测试。"""

import json

from core.enums import ImportTaskStatus
from schema.import_schema import ImportInputFormat, ImportMetadata, ImportRequest, ImportStage
from services.import_service import ImportService, ImportTaskNotFoundError
from utils.memory_import_adapters import (
    DeterministicEmbeddingModel,
    InMemoryChunkRepository,
    InMemoryImportTaskRepository,
    InMemoryQuestionRepository,
    InMemorySourceObjectStore,
    InMemoryVectorIndex,
)


def build_service(
    *,
    embedding_mismatch: bool = False,
    storage_fail: bool = False,
) -> tuple[
    ImportService,
    InMemoryImportTaskRepository,
    InMemoryChunkRepository,
    InMemoryQuestionRepository,
    InMemoryVectorIndex,
]:
    """构建带内存适配器的导入服务，方便测试检查副作用。"""
    task_repository = InMemoryImportTaskRepository()
    chunk_repository = InMemoryChunkRepository()
    question_repository = InMemoryQuestionRepository()
    vector_index = InMemoryVectorIndex()
    service = ImportService(
        task_repository=task_repository,
        source_store=InMemorySourceObjectStore(fail=storage_fail),
        chunk_repository=chunk_repository,
        question_repository=question_repository,
        embedding_model=DeterministicEmbeddingModel(mismatch=embedding_mismatch),
        vector_index=vector_index,
    )
    return service, task_repository, chunk_repository, question_repository, vector_index


def document_request(*, force_reimport: bool = False) -> ImportRequest:
    """创建标准文档导入请求。"""
    return ImportRequest(
        file_name="lesson.md",
        input_format=ImportInputFormat.MARKDOWN,
        source_text="# Python\n\nFunctions use def.",
        force_reimport=force_reimport,
        metadata=ImportMetadata(course_name="Python Intro", chapter_name="Functions"),
    )


def test_successful_document_import_with_memory_adapters() -> None:
    """文档导入成功时应写入片段、向量记录并完成任务。"""
    service, _, chunk_repository, _, vector_index = build_service()

    result = service.submit_and_run(document_request())

    assert result.task.status == ImportTaskStatus.COMPLETED
    assert result.task.progress == 100
    assert result.task.chunk_count == len(chunk_repository.chunks)
    assert len(vector_index.records) == result.task.chunk_count


def test_embedding_mismatch_fails_task() -> None:
    """Embedding 返回数量不一致时任务应失败并记录错误。"""
    service, _, _, _, _ = build_service(embedding_mismatch=True)

    result = service.submit_and_run(document_request())

    assert result.task.status == ImportTaskStatus.FAILED
    assert result.task.stage == ImportStage.FAILED
    assert "Embedding" in (result.task.error or "")


def test_storage_failure_fails_before_parsing() -> None:
    """原始文件保存失败时不应继续解析和入库。"""
    service, _, chunk_repository, _, _ = build_service(storage_fail=True)

    result = service.submit_and_run(document_request())

    assert result.task.status == ImportTaskStatus.FAILED
    assert "对象存储不可用" in (result.task.error or "")
    assert chunk_repository.chunks == []


def test_duplicate_import_is_skipped_without_force() -> None:
    """相同租户、来源和哈希的重复导入应跳过重复入库。"""
    service, _, chunk_repository, _, _ = build_service()

    first = service.submit_and_run(document_request())
    second = service.submit_and_run(document_request())

    assert first.task.status == ImportTaskStatus.COMPLETED
    assert second.task.stage == ImportStage.SKIPPED_DUPLICATE
    assert second.task.duplicate_of_task_id == first.task.task_id
    assert len(chunk_repository.chunks) == first.task.chunk_count


def test_force_reimport_creates_new_records() -> None:
    """开启 force_reimport 时应绕过重复跳过策略。"""
    service, _, chunk_repository, _, _ = build_service()

    first = service.submit_and_run(document_request())
    second = service.submit_and_run(document_request(force_reimport=True))

    assert second.task.status == ImportTaskStatus.COMPLETED
    assert second.task.duplicate_of_task_id is None
    assert len(chunk_repository.chunks) == first.task.chunk_count + second.task.chunk_count


def test_question_bank_import_persists_questions() -> None:
    """题库导入应保存结构化题目记录。"""
    service, _, _, question_repository, _ = build_service()
    request = ImportRequest(
        file_name="questions.json",
        input_format=ImportInputFormat.QUESTION_JSON,
        source_text=json.dumps(
            [
                {
                    "question_type": "single_choice",
                    "stem": "Which keyword defines a function?",
                    "options": ["func", "def"],
                    "answer": "def",
                }
            ]
        ),
        metadata=ImportMetadata(course_name="Python Intro", chapter_name="Functions"),
    )

    result = service.submit_and_run(request)

    assert result.task.status == ImportTaskStatus.COMPLETED
    assert result.task.question_count == 1
    assert question_repository.questions[0].source_file_name == "questions.json"


def test_get_missing_task_raises_not_found() -> None:
    """查询不存在任务时应抛出明确错误。"""
    service, _, _, _, _ = build_service()

    try:
        service.get_task("missing")
    except ImportTaskNotFoundError as exc:
        assert exc.args[0] == "missing"
    else:
        raise AssertionError("expected ImportTaskNotFoundError")
