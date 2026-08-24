"""测试全局 fixture。"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def warmup_model():
    """预热 Embedding 模型，规避 torch 与 pymysql 在 Windows 下的原生库冲突。"""
    from app.rag.embedder import embed

    embed(["预热"])
    yield
