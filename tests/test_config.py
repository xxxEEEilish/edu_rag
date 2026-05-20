"""配置加载测试。

这些测试确保基础配置在没有真实 `.env`、数据库和模型凭据时也能加载。
"""

from core.config import Settings


def test_settings_load_defaults() -> None:
    """默认配置应满足本地开发和离线单元测试的最低启动要求。"""
    settings = Settings()

    assert settings.app_name == "edu-rag"
    assert settings.default_tenant_id == "default"
    assert settings.embedding_dim == 1536
    assert settings.mongo_db_name == "edu_rag"
    assert settings.docx_parse_mode == "python-docx"
