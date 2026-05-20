"""应用启动入口。

本模块只负责组装 FastAPI 应用和挂载基础路由，避免在导入阶段连接
MongoDB、Milvus、MinIO 或模型服务。这样后续测试、CLI 导入和本地启动
都不会被外部依赖阻塞。
"""

from fastapi import FastAPI

from api.health_router import router as health_router
from core.config import get_settings


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。

    这里读取配置只使用本地环境变量和默认值，不触发任何网络连接。
    后续导入链路、查询链路和管理后台都应通过独立 router 挂载到该应用。
    """
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    # 健康检查是最小可观测能力，用于启动验证、部署探针和本地调试。
    app.include_router(health_router)
    return app


# ASGI 服务器（如 uvicorn）默认加载的应用对象。
app = create_app()
