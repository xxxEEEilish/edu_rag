"""集中式配置加载。

本模块定义项目运行所需的全部基础配置。配置值优先来自 `.env` 或环境变量，
没有提供时使用适合本地开发的安全默认值。所有业务模块应通过 `get_settings`
读取配置，避免在各处直接访问环境变量导致配置分散。
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """教育 RAG 服务的配置契约。

    字段按用途分组：应用基础配置、模型配置、向量库、文档库、对象存储、
    DOCX 解析配置。后续实现真实适配器时应复用这些字段，而不是新增散落的
    环境变量读取逻辑。
    """

    # 允许从 `.env` 自动加载配置；extra=ignore 让本地额外变量不会破坏启动。
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用基础信息和端口配置，供 FastAPI、导入服务和查询服务复用。
    app_name: str = "edu-rag"
    app_version: str = "0.1.0"
    debug: bool = False
    default_tenant_id: str = "default"
    import_service_port: int = 8000
    query_service_port: int = 8001

    # LLM 与视觉语言模型配置。密钥默认为空，避免测试环境要求真实凭据。
    openai_api_key: str = ""
    openai_api_base: str = ""
    llm_default_model: str = "qwen-flash"
    llm_default_temperature: float = 0.1
    vl_model: str = "qwen3-vl-flash"

    # Embedding 与 Reranker 配置，后续向量化、重排和题库检索会复用。
    bge_m3_path: str = ""
    bge_device: str = "cuda:0"
    bge_fp16: bool = True
    bge_reranker_large: str = ""
    bge_reranker_device: str = "cuda:0"
    embedding_model: str = "text-embedding-v4"
    embedding_dim: int = 1536

    # Milvus 集合命名在基础阶段固定，保证导入和检索阶段使用同一套约定。
    milvus_url: str = "http://localhost:19530"
    milvus_chunks_collection: str = "edu_kb_chunks"
    milvus_questions_collection: str = "edu_questions"
    milvus_course_names_collection: str = "edu_course_names"
    milvus_video_segments_collection: str = "edu_video_segments"
    milvus_multimodal_collection: str = "edu_multimodal_assets"
    milvus_metric_type: str = "COSINE"
    milvus_min_cosine_score: float = 0.75

    # MongoDB 保存课程、文档、题目、导入任务和会话历史等结构化元数据。
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db_name: str = "edu_rag"

    # MinIO 用于保存原始上传文件、解析产物、课件图片和后续导出文件。
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    # secret 不参与 repr，避免测试失败或日志输出时泄露敏感信息。
    minio_secret_key: str = Field(default="minioadmin", repr=False)
    minio_bucket_name: str = "edu-knowledge-base"
    minio_secure: bool = False

    # DOCX 是一期正式支持的导入格式，这里预留解析策略和行为开关。
    docx_parse_mode: str = "python-docx"
    docx_enable_table_parse: bool = True
    docx_enable_image_placeholder: bool = True


@lru_cache
def get_settings() -> Settings:
    """返回缓存后的配置对象。

    配置读取会被 API、服务、适配器和测试频繁调用；缓存可以避免重复解析
    `.env`，同时保持调用方拿到一致的配置快照。
    """
    return Settings()
