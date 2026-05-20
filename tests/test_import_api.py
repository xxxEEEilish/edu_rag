"""内容导入 API 测试。"""

from fastapi.testclient import TestClient

from main import app


def test_submit_import_api() -> None:
    """提交合法导入请求应返回完成状态和任务 ID。"""
    client = TestClient(app)

    response = client.post(
        "/imports",
        json={
            "file_name": "api-lesson.md",
            "input_format": "markdown",
            "source_text": "# Python\n\nFunctions use def.",
            "metadata": {
                "tenant_id": "api_tenant",
                "course_name": "Python Intro",
                "chapter_name": "Functions",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["progress"] == 100
    assert payload["task_id"]


def test_import_api_validation_failure() -> None:
    """缺少 source_text 时 API 应返回请求校验错误。"""
    client = TestClient(app)

    response = client.post(
        "/imports",
        json={
            "file_name": "invalid.md",
            "metadata": {"course_name": "Python Intro"},
        },
    )

    assert response.status_code == 422


def test_get_import_status_api() -> None:
    """提交后应能通过任务 ID 查询状态详情。"""
    client = TestClient(app)
    created = client.post(
        "/imports",
        json={
            "file_name": "status-lesson.md",
            "input_format": "markdown",
            "source_text": "# Python\n\nFunctions use def.",
            "metadata": {"course_name": "Python Intro"},
        },
    ).json()

    response = client.get(f"/imports/{created['task_id']}")

    assert response.status_code == 200
    assert response.json()["task_id"] == created["task_id"]


def test_get_missing_import_status_api() -> None:
    """不存在的任务 ID 应返回 404。"""
    client = TestClient(app)

    response = client.get("/imports/missing")

    assert response.status_code == 404
