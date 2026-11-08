"""测试全局配置：测试库与向量索引独立于正式数据。

环境变量优先级高于 .env，必须在导入 app 之前设置。
"""
import os
import shutil
import tempfile

import pytest

_TEST_DB = os.environ.get("TEST_MYSQL_DATABASE", "travel_kb_test")
_TEST_STORE = tempfile.mkdtemp(prefix="jwzh-test-store-")
os.environ["MYSQL_DATABASE"] = _TEST_DB
os.environ["VECTOR_STORE_DIR"] = _TEST_STORE
os.environ["API_KEY"] = ""


@pytest.fixture(autouse=True)
def _no_real_metadata_llm(monkeypatch):
    """导入测试默认不调用真实 LLM，需要兜底结果的用例自行覆盖。"""
    from app.services import import_service

    monkeypatch.setattr(import_service, "extract_metadata", lambda _content: {})


@pytest.fixture(scope="session")
def database():
    """创建独立测试库并建表，结束后删除；MySQL 不可用时跳过依赖它的测试。"""
    assert _TEST_DB.endswith("_test"), "测试库名必须以 _test 结尾，防止误删正式库"

    import pymysql

    from app.config import settings

    try:
        conn = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
        )
    except pymysql.err.OperationalError as exc:
        pytest.skip(f"MySQL 不可用：{exc}")

    with conn.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{_TEST_DB}` CHARACTER SET utf8mb4")

    # 先加载模型再连接数据库，规避 torch 与 pymysql 在 Windows 下的原生库冲突
    from app.rag.embedder import embed

    embed(["预热"])

    from app.models import engine, init_db

    init_db()
    yield
    engine.dispose()
    with conn.cursor() as cursor:
        cursor.execute(f"DROP DATABASE IF EXISTS `{_TEST_DB}`")
    conn.close()
    shutil.rmtree(_TEST_STORE, ignore_errors=True)
