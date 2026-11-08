"""元数据 LLM 兜底（TDD §7.3）。"""
import pytest

from app.config import settings
from app.core.resilience import ExternalServiceError
from app.models import Document, SessionLocal
from app.rag import generator
from app.rag.normalizer import NormalizedMetadata, fill_missing, needs_llm_fallback
from app.services import import_service
from app.services.import_service import get_task, import_document

COMPLETE = NormalizedMetadata(content_type="景点介绍", region="三亚", name="亚龙湾")


def test_complete_metadata_needs_no_fallback():
    assert not needs_llm_fallback(COMPLETE)


@pytest.mark.parametrize(
    "meta",
    [
        NormalizedMetadata(content_type="未知", region="三亚", name="亚龙湾"),
        NormalizedMetadata(content_type="景点介绍", name="亚龙湾"),
        NormalizedMetadata(content_type="景点介绍", region="三亚"),
    ],
)
def test_incomplete_metadata_needs_fallback(meta):
    assert needs_llm_fallback(meta)


def test_fill_missing_keeps_declared_values():
    meta = NormalizedMetadata(content_type="线路推荐", region="三亚")
    fill_missing(meta, {"content_type": "景点介绍", "region": "杭州", "name": "西湖", "theme": "湖景"})
    assert (meta.content_type, meta.region, meta.name, meta.theme) == ("线路推荐", "三亚", "西湖", "湖景")


def test_fill_missing_normalizes_content_type_alias():
    meta = NormalizedMetadata()
    fill_missing(meta, {"content_type": "美食推荐"})
    assert meta.content_type == "美食介绍"


@pytest.mark.parametrize("value", ["随便写的类型", 123, None, ["景点介绍"]])
def test_fill_missing_discards_invalid_content_type(value):
    meta = NormalizedMetadata(content_type="未知")
    fill_missing(meta, {"content_type": value})
    assert meta.content_type == "未知"


def test_fill_missing_discards_non_string_and_truncates():
    meta = NormalizedMetadata()
    fill_missing(meta, {"region": "长" * 100, "name": {"x": 1}, "theme": 5})
    assert (len(meta.region), meta.name, meta.theme) == (64, "", "")


class TestExtractMetadata:
    @pytest.fixture(autouse=True)
    def _key(self, monkeypatch):
        monkeypatch.setattr(settings, "deepseek_api_key", "k")

    def test_returns_parsed_json(self, monkeypatch):
        seen = {}

        def fake(**kwargs):
            seen.update(kwargs)
            return '{"region": "三亚"}'

        monkeypatch.setattr(generator, "_complete", fake)
        assert generator.extract_metadata("文档 {含大括号}") == {"region": "三亚"}
        assert "文档 {含大括号}" in seen["messages"][0]["content"]
        assert seen["response_format"] == {"type": "json_object"}

    def test_truncates_long_documents(self, monkeypatch):
        seen = {}

        def fake(**kwargs):
            seen.update(kwargs)
            return "{}"

        monkeypatch.setattr(generator, "_complete", fake)
        generator.extract_metadata("字" * 100000)
        assert seen["messages"][0]["content"].count("字") <= 3100

    @pytest.mark.parametrize("output", ["不是 JSON", "[1, 2]", '"文本"'])
    def test_bad_output_returns_empty(self, monkeypatch, output):
        monkeypatch.setattr(generator, "_complete", lambda **_kw: output)
        assert generator.extract_metadata("文档") == {}

    def test_llm_failure_returns_empty(self, monkeypatch):
        def fail(**_kwargs):
            raise ExternalServiceError("llm")

        monkeypatch.setattr(generator, "_complete", fail)
        assert generator.extract_metadata("文档") == {}

    def test_skips_call_without_llm_key(self, monkeypatch):
        monkeypatch.setattr(settings, "deepseek_api_key", "")
        monkeypatch.setattr(generator, "_complete", lambda **_kw: pytest.fail("不应调用 LLM"))
        assert generator.extract_metadata("文档") == {}


def _import(tmp_path, content):
    path = tmp_path / "兜底.md"
    path.write_text(content, encoding="utf-8")
    return get_task(import_document(str(path), source_file="兜底.md"))


def _document():
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.source_file == "兜底.md").one()
        return doc.content_type, doc.region, doc.name
    finally:
        db.close()


@pytest.mark.usefixtures("database")
class TestImportWithFallback:
    def test_llm_rescues_document_without_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            import_service,
            "extract_metadata",
            lambda _c: {"content_type": "景点介绍", "region": "三亚", "name": "亚龙湾"},
        )
        task = _import(tmp_path, "# 亚龙湾\n## 概览\n三亚的海湾。")
        assert task["status"] == "success"
        assert _document() == ("景点介绍", "三亚", "亚龙湾")

    def test_document_still_fails_when_llm_cannot_help(self, tmp_path):
        task = _import(tmp_path, "# 亚龙湾\n## 概览\n三亚的海湾。")
        assert task["status"] == "failed" and "内容类型无效" in task["error_message"]

    def test_complete_document_does_not_call_llm(self, tmp_path, monkeypatch):
        monkeypatch.setattr(import_service, "extract_metadata", lambda _c: pytest.fail("不应调用 LLM"))
        task = _import(
            tmp_path,
            "# 亚龙湾\n## 元数据\n- 内容类型：景点介绍\n- 城市：三亚\n- 景点名称：亚龙湾\n\n## 概览\n海湾。",
        )
        assert task["status"] == "success"

    def test_empty_body_does_not_call_llm(self, tmp_path, monkeypatch):
        monkeypatch.setattr(import_service, "extract_metadata", lambda _c: pytest.fail("不应调用 LLM"))
        task = _import(tmp_path, "# 无正文\n## 元数据\n- 内容类型：景点介绍\n")
        assert task["status"] == "failed" and "正文为空" in task["error_message"]
