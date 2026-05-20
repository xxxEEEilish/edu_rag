"""应用启动入口。

本模块只负责组装 FastAPI 应用和挂载路由，不在启动阶段连接 MongoDB、Milvus、
MinIO 或模型服务。这样本地开发、单元测试和 CLI 导入都不会被外部依赖阻塞。
"""

from fastapi import FastAPI

from api.health_router import router as health_router
from api.import_router import router as import_router
from core.config import get_settings


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。

    这里读取配置只使用本地环境变量和默认值，不触发任何网络连接。导入、查询和后台
    管理能力都通过独立 router 挂载，便于后续按模块替换依赖或关闭功能。
    """
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    # 健康检查用于启动验证、部署探针和本地调试，必须保持轻量。
    app.include_router(health_router)
    # 内容导入路由默认使用内存适配器，确保应用启动不依赖外部数据库、对象存储或模型服务。
    app.include_router(import_router)
    return app


# ASGI 服务加载的应用对象，例如 `uvicorn main:app --reload`。
app = create_app()
