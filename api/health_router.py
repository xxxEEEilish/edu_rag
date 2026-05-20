"""健康检查路由。

该路由用于确认应用进程已启动、配置可读取。它刻意不检查数据库、
对象存储或模型服务，因为这些外部依赖会在后续阶段按各自能力接入。
"""

from fastapi import APIRouter

from core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """返回应用基础运行状态。

    返回内容保持精简，便于前端、本地测试和部署平台统一判断服务是否存活。
    """
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }
