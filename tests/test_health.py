"""健康检查接口测试。

健康检查必须保持轻量，不能因为外部服务未启动而失败。
"""

from fastapi.testclient import TestClient

from main import app


def test_health_check() -> None:
    """请求 `/health` 时应返回可用于部署探针的成功状态。"""
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
