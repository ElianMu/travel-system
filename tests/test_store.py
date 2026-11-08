"""向量索引单元测试（S1 验收）。"""
from app.rag.store import VectorStore


def _meta(document_id, region="三亚", content_type="景点介绍"):
    return {"document_id": document_id, "region": region, "content_type": content_type}


def _store(tmp_path):
    store = VectorStore(str(tmp_path / "index.npz"))
    store.add(
        ["a", "b", "c"],
        ["甲", "乙", "丙"],
        [[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]],
        [_meta(1), _meta(2, region="昆明、大理、丽江"), _meta(3, content_type="线路推荐")],
    )
    return store


def test_query_orders_by_similarity(tmp_path):
    result = _store(tmp_path).query([1.0, 0.0], top_k=2)
    assert result["ids"][0] == ["a", "b"]


def test_filter_by_metadata(tmp_path):
    result = _store(tmp_path).query([1.0, 0.0], where={"content_type": "线路推荐"})
    assert result["ids"][0] == ["c"]


def test_filter_by_substring(tmp_path):
    result = _store(tmp_path).query([1.0, 0.0], where={"region": {"$contains": "大理"}})
    assert result["ids"][0] == ["b"]


def test_delete_by_document_and_persistence(tmp_path):
    store = _store(tmp_path)
    store.delete_by_document(1)
    reloaded = VectorStore(str(tmp_path / "index.npz"))
    assert reloaded.count() == 2
    assert reloaded.query([1.0, 0.0], top_k=1)["ids"][0] == ["b"]


def test_add_after_all_deleted(tmp_path):
    store = _store(tmp_path)
    for document_id in (1, 2, 3):
        store.delete_by_document(document_id)
    store.add(["d"], ["丁"], [[1.0, 0.0]], [_meta(4)])
    assert store.query([1.0, 0.0])["ids"][0] == ["d"]
