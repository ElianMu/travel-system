"""端到端集成测试：导入 → 检索。"""
import os

from app.models import SessionLocal, Document, ImportTask
from app.rag.retriever import retrieve
from app.services.import_service import import_document


def test_import_and_retrieve(tmp_path):
    """导入单份文档后，检索能命中并返回来源信息。"""
    src = tmp_path / "测试景点.md"
    src.write_text(
        "# 测试景点\n## 元数据\n- 内容类型：景点介绍\n- 城市：测试城\n- 景点名称：测试景点\n- 主题：测试\n\n"
        "## 目的地概览\n测试景点是一个适合亲子游的海滨景区。\n",
        encoding="utf-8",
    )

    task_id = import_document(str(src), source_file="测试景点.md")
    db = SessionLocal()
    task = db.get(ImportTask, task_id)
    assert task is not None and task.status == "success"
    db.close()

    hits = retrieve("适合亲子的海滨景区", top_k=3, content_type="景点介绍")
    assert len(hits) > 0
    assert hits[0]["content_type"] == "景点介绍"
    assert hits[0]["source_file"] == "测试景点.md"

    # 清理
    db = SessionLocal()
    doc = db.query(Document).filter(Document.source_file == "测试景点.md").first()
    if doc:
        from app.rag.store import get_vector_store

        get_vector_store().delete_by_document(doc.id)
        db.delete(doc)
        db.commit()
    db.close()
