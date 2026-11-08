"""导入编排、失败隔离与安全校验（S4 验收）。"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.security import UPLOAD_DIR, is_allowed_path, is_safe_filename
from app.main import app
from app.models import Chunk, Document, SessionLocal
from app.rag.store import get_vector_store
from app.services import import_service
from app.services.import_service import get_task, import_document, rebuild_vector_index

VALID_DOC = (
    "# {name}\n## 元数据\n- 内容类型：景点介绍\n- 城市：测试城\n- 景点名称：{name}\n- 主题：海滨\n\n"
    "## 概览\n{name}是一处海滨景区。\n"
)


def _write(tmp_path, filename, name="测试景点"):
    path = tmp_path / filename
    path.write_text(VALID_DOC.format(name=name), encoding="utf-8")
    return str(path)


def _documents(source_file):
    db = SessionLocal()
    try:
        return [d.id for d in db.query(Document).filter(Document.source_file == source_file)]
    finally:
        db.close()


def _vector_doc_ids(source_file):
    store = get_vector_store()
    return {m["document_id"] for m in store._metadatas if m["source_file"] == source_file}


@pytest.mark.usefixtures("database")
class TestImportPipeline:
    def test_success_keeps_all_stores_consistent(self, tmp_path):
        task = get_task(import_document(_write(tmp_path, "一致.md"), source_file="一致.md"))
        assert task["status"] == "success"
        assert task["processed_chunks"] == task["total_chunks"] == 1

        doc_ids = _documents("一致.md")
        assert len(doc_ids) == 1
        db = SessionLocal()
        assert db.query(Chunk).filter(Chunk.document_id == doc_ids[0]).count() == 1
        db.close()
        assert _vector_doc_ids("一致.md") == set(doc_ids)
        meta = next(m for m in get_vector_store()._metadatas if m["source_file"] == "一致.md")
        assert meta["theme"] == "海滨"

    def test_corrupted_document_is_isolated(self, tmp_path):
        broken = tmp_path / "损坏.md"
        broken.write_bytes(b"\xff\xfe\x00\x80binary")
        bad = get_task(import_document(str(broken), source_file="损坏.md"))
        good = get_task(import_document(_write(tmp_path, "正常.md"), source_file="正常.md"))

        assert bad["status"] == "failed" and bad["error_message"]
        assert good["status"] == "success"
        assert _documents("损坏.md") == []

    @pytest.mark.parametrize(
        ("content", "reason"),
        [
            ("# 无元数据\n## 正文\n内容", "内容类型无效"),
            ("# 错误类型\n## 元数据\n- 内容类型：未知\n\n## 正文\n内容", "内容类型无效"),
            ("# 无正文\n## 元数据\n- 内容类型：景点介绍\n", "正文为空"),
        ],
    )
    def test_invalid_documents_fail_with_reason(self, tmp_path, content, reason):
        path = tmp_path / "无效.md"
        path.write_text(content, encoding="utf-8")
        task = get_task(import_document(str(path), source_file="无效.md"))
        assert task["status"] == "failed"
        assert reason in task["error_message"]
        assert _documents("无效.md") == []

    def test_vector_write_failure_rolls_back(self, tmp_path, monkeypatch):
        def fail(*_args, **_kwargs):
            raise RuntimeError("磁盘已满")

        monkeypatch.setattr(get_vector_store(), "add", fail)
        task = get_task(import_document(_write(tmp_path, "写失败.md"), source_file="写失败.md"))
        assert task["status"] == "failed" and "磁盘已满" in task["error_message"]
        assert _documents("写失败.md") == []

    def test_failure_after_vector_write_removes_vectors(self, tmp_path, monkeypatch):
        def fail(*_args, **_kwargs):
            raise RuntimeError("提交前失败")

        monkeypatch.setattr(import_service, "_delete_previous_versions", fail)
        task = get_task(import_document(_write(tmp_path, "补偿.md"), source_file="补偿.md"))
        assert task["status"] == "failed"
        assert _documents("补偿.md") == []
        assert _vector_doc_ids("补偿.md") == set()

    def test_reimport_replaces_previous_version(self, tmp_path):
        path = _write(tmp_path, "重复.md")
        import_document(path, source_file="重复.md")
        first_ids = _documents("重复.md")
        import_document(path, source_file="重复.md")
        second_ids = _documents("重复.md")

        assert len(second_ids) == 1 and second_ids != first_ids
        assert _vector_doc_ids("重复.md") == set(second_ids)

    def test_rebuild_restores_index_from_database(self, tmp_path):
        import_document(_write(tmp_path, "重建.md"), source_file="重建.md")
        store = get_vector_store()
        expected = store.count()
        store.replace_all([], [], [], [])

        assert rebuild_vector_index() == expected
        assert store.count() == expected
        assert _vector_doc_ids("重建.md") == set(_documents("重建.md"))


@pytest.mark.usefixtures("database")
class TestImportApi:
    client = TestClient(app)

    def test_upload_and_query_task(self):
        resp = self.client.post(
            "/api/v1/import",
            files={"file": ("接口.md", VALID_DOC.format(name="接口").encode(), "text/markdown")},
        )
        assert resp.status_code == 200
        task = self.client.get(f"/api/v1/import/tasks/{resp.json()['task_id']}").json()
        assert task["status"] == "success"
        Path(UPLOAD_DIR, "接口.md").unlink()

    def test_rejects_non_markdown(self):
        resp = self.client.post("/api/v1/import", files={"file": ("a.exe", b"x")})
        assert resp.status_code == 400

    @pytest.mark.parametrize("filename", ["../../etc/evil.md", "..\\evil.md"])
    def test_rejects_path_traversal(self, filename):
        resp = self.client.post("/api/v1/import", files={"file": (filename, b"x")})
        assert resp.status_code == 403

    def test_unknown_task_returns_404(self):
        assert self.client.get("/api/v1/import/tasks/999999").status_code == 404


def test_path_whitelist():
    assert is_allowed_path("storage/uploads/a.md")
    assert not is_allowed_path("storage/uploads/../../.env")
    assert not is_allowed_path("data_evil/a.md")


@pytest.mark.parametrize("name", ["", ".", "..", "a/b.md", "a\\b.md", "a\0.md"])
def test_unsafe_filenames(name):
    assert not is_safe_filename(name)
