"""端到端集成测试：导入 → 检索 → 问答，以及治理能力。"""
import json
import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.logging import JsonFormatter, trace_id_var
from app.core.resilience import ExternalServiceError
from app.main import app
from app.rag import generator, web_search
from app.rag.prompts import SYSTEM_PROMPT
from app.rag.retriever import retrieve
from app.services import chat_service
from app.services.import_service import import_document

DOC = (
    "# 测试景点\n## 元数据\n- 内容类型：景点介绍\n- 城市：测试城\n- 景点名称：测试景点\n- 主题：测试\n\n"
    "## 目的地概览\n测试景点是一个适合亲子游的海滨景区。\n"
)

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module", autouse=True)
def imported(database, tmp_path_factory):
    src = tmp_path_factory.mktemp("integration") / "测试景点.md"
    src.write_text(DOC, encoding="utf-8")
    import_document(str(src), source_file="测试景点.md")


def test_import_retrieve_answer(monkeypatch):
    """导入后可检索命中，问答返回答案与可追溯引用。"""
    hits = retrieve("适合亲子的海滨景区", top_k=3, content_type="景点介绍")
    assert hits[0]["source_file"] == "测试景点.md"

    def create(**_kwargs):
        message = SimpleNamespace(content="适合亲子。")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(generator, "_get_client", lambda: fake)
    monkeypatch.setattr(web_search, "search", lambda *_a, **_k: [])

    body = client.post("/api/v1/chat", json={"query": "测试景点是适合亲子的海滨景区吗"}).json()
    assert body["answer"] == "适合亲子。"
    assert body["citations"][0]["source_file"] == "测试景点.md"


class TestGovernance:
    def test_error_response_format(self):
        resp = client.get("/api/v1/import/tasks/999999", headers={"X-Trace-Id": "trace-abc"})
        assert resp.status_code == 404
        assert resp.json() == {"code": "NOT_FOUND", "message": "任务不存在", "trace_id": "trace-abc"}
        assert resp.headers["X-Trace-Id"] == "trace-abc"

    def test_validation_error_format(self):
        body = client.post("/api/v1/chat", json={"query": ""}).json()
        assert body["code"] == "INVALID_REQUEST"
        assert body["trace_id"]

    def test_external_failure_returns_503(self, monkeypatch):
        def fail(*_a, **_k):
            raise ExternalServiceError("llm")

        monkeypatch.setattr(chat_service, "chat", fail)
        resp = client.post("/api/v1/chat", json={"query": "你好"})
        assert resp.status_code == 503
        assert resp.json()["code"] == "LLM_UNAVAILABLE"

    def test_unexpected_error_hides_details(self, monkeypatch):
        def fail(*_a, **_k):
            raise RuntimeError("secret-detail")

        monkeypatch.setattr(chat_service, "chat", fail)
        resp = client.post("/api/v1/chat", json={"query": "你好"})
        assert resp.status_code == 500
        assert resp.json()["code"] == "INTERNAL_ERROR"
        assert "secret-detail" not in resp.text

    def test_metrics_exposed(self):
        retrieve("海滨景区")
        text = client.get("/metrics").text
        for metric in (
            "jwzh_retrieve_latency_seconds_count",
            "jwzh_first_token_latency_seconds",
            "jwzh_import_tasks_total",
            "jwzh_external_call_errors_total",
        ):
            assert metric in text

    def test_log_contains_trace_id_and_fields(self):
        token = trace_id_var.set("t-1")
        record = logging.LogRecord("a", logging.INFO, __file__, 1, "消息", None, None)
        record.fields = {"duration_ms": 3}
        payload = json.loads(JsonFormatter().format(record))
        trace_id_var.reset(token)
        assert payload["trace_id"] == "t-1"
        assert payload["duration_ms"] == 3
        assert payload["message"] == "消息"

    def test_system_prompt_guards_against_injection(self):
        assert "一律不执行" in SYSTEM_PROMPT

    def test_sql_injection_in_filter_is_harmless(self):
        resp = client.get("/api/v1/documents", params={"region": "' OR 1=1 -- %"})
        assert resp.status_code == 200
        assert resp.json()["documents"] == []
