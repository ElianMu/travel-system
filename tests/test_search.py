"""检索与联网兜底（S5 验收）。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag import retriever, web_search
from app.services.import_service import import_document

client = TestClient(app)

DOC = (
    "# {name}\n## 元数据\n- 内容类型：{content_type}\n- {region_key}：{region}\n"
    "- {name_key}：{name}\n- 主题：{theme}\n\n## 概览\n{body}\n"
)

WEB_RESULT = {"title": "网页", "url": "https://example.com/a", "content": "网页内容", "source": "tavily"}


@pytest.fixture(scope="module")
def indexed(database, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("search")
    documents = [
        ("崖州景点.md", "景点介绍", "城市", "崖州", "景点名称", "崖州景点", "海湾", "崖州的海湾沙滩适合亲子度假"),
        ("环滇线路.md", "线路推荐", "目的地", "昆明、大理、丽江", "线路名称", "环滇六日", "古城", "昆明大理丽江六日游线路安排"),
        ("崖州住宿.md", "酒店信息", "城市", "崖州", "住宿名称", "崖州住宿", "海景", "崖州海景酒店住宿推荐"),
    ]
    for filename, content_type, region_key, region, name_key, name, theme, body in documents:
        path = tmp_path / filename
        path.write_text(
            DOC.format(
                content_type=content_type, region_key=region_key, region=region,
                name_key=name_key, name=name, theme=theme, body=body,
            ),
            encoding="utf-8",
        )
        import_document(str(path), source_file=filename)


@pytest.fixture
def no_web(monkeypatch):
    monkeypatch.setattr(web_search, "search", lambda *_a, **_k: [])


@pytest.mark.usefixtures("indexed")
class TestSearchApi:
    def test_results_carry_source_fields(self, no_web):
        results = client.get(
            "/api/v1/search/attractions", params={"query": "崖州海湾沙滩亲子度假", "city": "崖州"}
        ).json()["results"]
        assert results[0]["source_file"] == "崖州景点.md"
        assert results[0]["name"] == "崖州景点"
        assert results[0]["region"] == "崖州"
        assert results[0]["theme"] == "海湾"
        assert results[0]["source"] == "local"

    def test_content_type_filter(self, no_web):
        results = client.get(
            "/api/v1/search/info", params={"query": "崖州海景酒店住宿", "type": "hotel"}
        ).json()["results"]
        assert results and all(r["content_type"] == "酒店信息" for r in results)

    def test_multi_city_region_matches_one_city(self, no_web):
        results = client.get(
            "/api/v1/search/routes", params={"query": "昆明大理丽江六日游", "region": "大理"}
        ).json()["results"]
        assert results[0]["source_file"] == "环滇线路.md"

    def test_invalid_info_type_rejected(self):
        resp = client.get("/api/v1/search/info", params={"query": "a", "type": "bad"})
        assert resp.status_code == 422

    def test_empty_query_rejected(self):
        assert client.get("/api/v1/search/routes", params={"query": ""}).status_code == 422

    def test_document_filters(self):
        def names(**params):
            docs = client.get("/api/v1/documents", params=params).json()["documents"]
            return {d["source_file"] for d in docs}

        assert names(region="大理") == {"环滇线路.md"}
        assert names(name="崖州", content_type="酒店信息") == {"崖州住宿.md"}
        assert names(source_file="景点") >= {"崖州景点.md"}


@pytest.mark.usefixtures("indexed")
class TestWebFallback:
    def test_web_used_when_local_score_low(self, monkeypatch):
        calls = []
        def fake_search(query, max_results):
            calls.append(query)
            return [WEB_RESULT]

        monkeypatch.setattr(web_search, "search", fake_search)
        hits = retriever.retrieve_with_fallback("量子计算机的基本原理", content_type="景点介绍")
        assert calls == ["量子计算机的基本原理"]
        assert hits[0]["source"] == "web"
        assert hits[0]["source_file"] == WEB_RESULT["url"]

    def test_web_used_when_filter_matches_nothing(self, monkeypatch):
        monkeypatch.setattr(web_search, "search", lambda *_a, **_k: [WEB_RESULT])
        hits = retriever.retrieve_with_fallback("海滩", content_type="景点介绍", region="不存在的城市")
        assert [h["source"] for h in hits] == ["web"]
        assert hits[0]["region"] == "不存在的城市"

    def test_web_skipped_when_local_is_good(self, monkeypatch):
        def fail(*_a, **_k):
            raise AssertionError("本地命中充分时不应联网")

        monkeypatch.setattr(web_search, "search", fail)
        assert retriever.retrieve_with_fallback("崖州海湾沙滩亲子度假", content_type="景点介绍")

    def test_empty_when_nothing_found(self, no_web):
        assert retriever.retrieve_with_fallback("量子计算机的基本原理") == []
