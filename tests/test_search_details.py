"""检索结果的结构化字段（FR-ATTR-002、FR-ROUTE-001、FR-INFO-001/002）。"""
import pytest

from app.rag.store import VectorStore
from app.services import search_service


@pytest.fixture
def store(tmp_path, monkeypatch):
    vector_store = VectorStore(str(tmp_path / "index.npz"))
    entries = [
        (1, "目的地概览", "## 目的地概览\n海湾与沙滩。"),
        (1, "适合人群 > 亲子", "## 适合人群\n### 亲子\n适合亲子游客。"),
        (1, "适合人群 > 情侣", "### 情侣\n适合情侣。"),
        (2, "适合人群", "## 适合人群\n另一份文档的人群。"),
        (2, "常见决策点", "## 常见决策点\n提前订票。"),
    ]
    vector_store.add(
        ids=[f"v{i}" for i in range(len(entries))],
        documents=[text for _, _, text in entries],
        embeddings=[[1.0, 0.0]] * len(entries),
        metadatas=[{"document_id": doc, "heading_path": path} for doc, path, _ in entries],
    )
    monkeypatch.setattr(search_service, "get_vector_store", lambda: vector_store)
    return vector_store


def _search(monkeypatch, search, hits):
    monkeypatch.setattr(search_service, "retrieve_with_fallback", lambda *_a, **_k: hits)
    return search("问题")


@pytest.mark.usefixtures("store")
def test_attraction_details_come_from_document_sections(monkeypatch):
    hits = [{"document_id": 1, "content_type": "景点介绍"}]
    details = _search(monkeypatch, search_service.search_attractions, hits)[0]["details"]

    assert details["景区特色"] == "海湾与沙滩。"
    assert details["适合人群"] == "亲子\n适合亲子游客。\n情侣\n适合情侣。"


@pytest.mark.usefixtures("store")
def test_field_without_section_stays_empty(monkeypatch):
    hits = [{"document_id": 1, "content_type": "景点介绍"}]
    details = _search(monkeypatch, search_service.search_attractions, hits)[0]["details"]

    assert details["最佳游览时间"] == ""


@pytest.mark.usefixtures("store")
def test_details_do_not_mix_documents(monkeypatch):
    hits = [{"document_id": 2, "content_type": "酒店信息"}]
    details = _search(monkeypatch, search_service.search_info, hits)[0]["details"]

    assert details["适合人群"] == "另一份文档的人群。"
    assert details["实用 tips"] == "提前订票。"
    assert details["详细信息"] == ""


@pytest.mark.usefixtures("store")
@pytest.mark.parametrize(
    ("name", "days"),
    [
        ("三亚 5 日经典游", "5 日"),
        ("厦门鼓浪屿 2 至 3 日游", "2 至 3 日"),
        ("环滇六日", "六日"),
        ("张家界天门山线路", ""),
        (None, ""),
    ],
)
def test_route_days_parsed_from_name(monkeypatch, name, days):
    hits = [{"document_id": 1, "content_type": "线路推荐", "name": name}]
    details = _search(monkeypatch, search_service.search_routes, hits)[0]["details"]

    assert details["行程天数"] == days


@pytest.mark.usefixtures("store")
def test_web_hits_have_empty_details(monkeypatch):
    hits = [{"content_type": "景点介绍", "source": "web"}]
    assert _search(monkeypatch, search_service.search_attractions, hits)[0]["details"] == {}


def test_long_section_is_truncated(store, monkeypatch):
    store.add(["long"], ["## 适合人群\n" + "字" * 1000], [[1.0, 0.0]],
              [{"document_id": 3, "heading_path": "适合人群"}])
    hits = [{"document_id": 3, "content_type": "景点介绍"}]
    details = _search(monkeypatch, search_service.search_attractions, hits)[0]["details"]

    assert len(details["适合人群"]) == 300
