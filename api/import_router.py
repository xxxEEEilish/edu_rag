"""内容导入 API 路由。

首期路由提供 JSON 方式提交导入任务和查询任务状态。为保持本地启动离线可用，默认
服务使用内存适配器；生产环境后续可通过依赖注入替换为真实 MongoDB、MinIO、Milvus
和 Embedding 适配器。
"""

from fastapi import APIRouter, HTTPException

from schema.import_schema import ImportRequest, ImportTaskDetail
from services.import_service import ImportService, ImportTaskNotFoundError
from utils.memory_import_adapters import (
    DeterministicEmbeddingModel,
    InMemoryChunkRepository,
    InMemoryImportTaskRepository,
    InMemoryQuestionRepository,
    InMemorySourceObjectStore,
    InMemoryVectorIndex,
)

router = APIRouter(prefix="/imports", tags=["imports"])


def build_default_import_service() -> ImportService:
    """构建离线可启动的默认导入服务。

    该默认实例面向开发和测试，不承担生产持久化职责；真实部署时应替换为外部服务
    适配器，API 层无需随之改变。
    """
    return ImportService(
        task_repository=InMemoryImportTaskRepository(),
        source_store=InMemorySourceObjectStore(),
        chunk_repository=InMemoryChunkRepository(),
        question_repository=InMemoryQuestionRepository(),
        embedding_model=DeterministicEmbeddingModel(),
        vector_index=InMemoryVectorIndex(),
    )


import_service = build_default_import_service()


@router.post("", response_model=ImportTaskDetail)
def submit_import(request: ImportRequest) -> ImportTaskDetail:
    """提交并执行内容导入任务。

    首期实现同步执行，响应中直接返回最终任务状态；后续接入后台任务后可调整为返回
    `pending` 状态，但任务详情模型保持不变。
    """
    result = import_service.submit_and_run(request)
    return result.task


@router.get("/{task_id}", response_model=ImportTaskDetail)
def get_import_task(task_id: str) -> ImportTaskDetail:
    """查询导入任务状态。"""
    try:
        return import_service.get_task(task_id)
    except ImportTaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="导入任务不存在") from exc
