"""问答、引用、流式、多轮与历史（S6、S7 验收）。LLM 用替身，其余走真实链路。"""
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag import generator, web_search
from app.services.import_service import import_document

client = TestClient(app)

DOC = (
    "# 崖州攻略\n## 元数据\n- 内容类型：景点介绍\n- 城市：崖州\n- 景点名称：崖州攻略\n- 主题：海湾\n\n"
    "## 核心景点\n崖州的海湾沙滩适合亲子度假，推荐停留两天。\n"
)
QUESTION = "崖州的海湾沙滩适合亲子度假吗"


class FakeLLM:
    """替代 OpenAI 客户端，记录收到的请求。"""

    def __init__(self, answer="崖州海湾适合亲子。", rewritten=QUESTION):
        self.answer = answer
        self.rewritten = rewritten
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        is_generation = kwargs["messages"][0]["role"] == "system"
        content = self.answer if is_generation else self.rewritten
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def parse_sse(text):
    events = []
    for block in text.replace("\r\n", "\n").strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.split("\n") if ": " in line)
        if "event" in fields:
            events.append((fields["event"], json.loads(fields["data"])))
    return events


def stream(query=QUESTION, session_id=None):
    resp = client.post("/api/v1/chat/stream", json={"query": query, "session_id": session_id})
    assert resp.status_code == 200
    return parse_sse(resp.text)


def new_session():
    return client.post("/api/v1/sessions", params={"title": "测试"}).json()["session_id"]


def messages_of(session_id):
    return client.get(f"/api/v1/sessions/{session_id}/messages").json()["messages"]


@pytest.fixture(scope="module", autouse=True)
def indexed(database, tmp_path_factory):
    path = tmp_path_factory.mktemp("chat") / "崖州攻略.md"
    path.write_text(DOC, encoding="utf-8")
    import_document(str(path), source_file="崖州攻略.md")


@pytest.fixture(autouse=True)
def isolate_network(monkeypatch):
    monkeypatch.setattr(web_search, "search", lambda *_a, **_k: [])


@pytest.fixture
def llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(generator, "_get_client", lambda: fake)
    return fake


def fake_stream(monkeypatch, tokens):
    async def _stream(_query, _hits):
        for token in tokens:
            if isinstance(token, Exception):
                raise token
            yield token

    monkeypatch.setattr(generator, "stream_generate", _stream)


class TestChat:
    def test_answer_with_citations(self, llm):
        body = client.post("/api/v1/chat", json={"query": QUESTION}).json()
        assert body["answer"] == llm.answer
        citation = body["citations"][0]
        assert citation["source_file"] == "崖州攻略.md"
        assert citation["heading_path"] == "核心景点"
        assert citation["score"] > 0
        assert "海湾沙滩" in citation["excerpt"]
        assert citation["chunk_id"].startswith("doc-")

    def test_prompt_contains_source_for_citation(self, llm):
        client.post("/api/v1/chat", json={"query": QUESTION})
        user_prompt = llm.requests[-1]["messages"][1]["content"]
        assert "来源：崖州攻略.md（核心景点）" in user_prompt

    def test_unanswerable_does_not_call_llm(self, llm):
        body = client.post("/api/v1/chat", json={"query": "量子计算机的基本原理"}).json()
        assert "无法回答" in body["answer"]
        assert body["citations"] == []
        assert llm.requests == []

    def test_refusal_has_no_citations(self, llm):
        llm.answer = "根据现有知识库无法回答。"
        assert client.post("/api/v1/chat", json={"query": QUESTION}).json()["citations"] == []

    def test_query_length_limited(self):
        assert client.post("/api/v1/chat", json={"query": "问" * 2001}).status_code == 422
        assert client.post("/api/v1/chat", json={"query": ""}).status_code == 422

    def test_unknown_session_returns_404(self):
        body = {"query": "你好", "session_id": "missing"}
        assert client.post("/api/v1/chat", json=body).status_code == 404
        assert client.post("/api/v1/chat/stream", json=body).status_code == 404


class TestStreaming:
    def test_tokens_then_done_with_citations(self, monkeypatch):
        fake_stream(monkeypatch, ["崖州", "适合"])
        events = stream()
        assert [e for e, _ in events] == ["token", "token", "done"]
        assert "".join(d["delta"] for e, d in events if e == "token") == "崖州适合"
        assert events[-1][1]["citations"][0]["source_file"] == "崖州攻略.md"

    def test_stream_error_falls_back_to_full_answer(self, monkeypatch, llm):
        fake_stream(monkeypatch, ["半截", RuntimeError("断流")])
        session_id = new_session()
        events = stream(session_id=session_id)
        assert ("message", {"answer": llm.answer}) in events
        assert events[-1][0] == "done" and events[-1][1]["citations"]
        # 降级时只落库一轮，内容是完整答案
        assert [m["content"] for m in messages_of(session_id)] == [QUESTION, llm.answer]

    def test_empty_stream_falls_back(self, monkeypatch, llm):
        fake_stream(monkeypatch, [])
        assert ("message", {"answer": llm.answer}) in stream()

    def test_both_paths_failing_emits_error_event(self, monkeypatch):
        fake_stream(monkeypatch, [RuntimeError("断流")])

        def broken_client():
            raise RuntimeError("LLM 不可用")

        monkeypatch.setattr(generator, "_get_client", broken_client)
        events = stream()
        assert events[-1][0] == "error"
        assert events[-1][1]["message"]

    def test_unanswerable_is_recorded(self):
        session_id = new_session()
        stream("量子计算机的基本原理", session_id)
        assert [m["role"] for m in messages_of(session_id)] == ["user", "assistant"]

    @pytest.mark.parametrize("status", [401, 500])
    def test_http_error_raises_for_fallback(self, monkeypatch, status):
        """上游返回错误状态时必须抛异常，否则会得到空答案且不触发降级。"""
        transport = httpx.MockTransport(lambda _req: httpx.Response(status, text="err"))
        real_client = httpx.AsyncClient
        monkeypatch.setattr(
            httpx, "AsyncClient", lambda **kw: real_client(transport=transport, **kw)
        )

        async def consume():
            return [t async for t in generator.stream_generate("问题", [{"content": "片段"}])]

        import asyncio

        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(consume())


class TestMultiTurn:
    def test_follow_up_uses_rewritten_query(self, llm):
        session_id = new_session()
        client.post("/api/v1/chat", json={"query": QUESTION, "session_id": session_id})
        llm.requests.clear()

        client.post("/api/v1/chat", json={"query": "那里呢", "session_id": session_id})

        rewrite_request, generate_request = llm.requests
        rewrite_prompt = rewrite_request["messages"][0]["content"]
        assert QUESTION in rewrite_prompt and "那里呢" in rewrite_prompt
        assert generate_request["messages"][1]["content"].endswith(f"问题：{QUESTION}")

    def test_rewrite_failure_uses_original_query(self, monkeypatch, llm):
        session_id = new_session()
        client.post("/api/v1/chat", json={"query": QUESTION, "session_id": session_id})

        def broken(*_a):
            raise RuntimeError("改写失败")

        monkeypatch.setattr(generator, "rewrite_query", broken)
        resp = client.post("/api/v1/chat", json={"query": QUESTION, "session_id": session_id})
        assert resp.json()["answer"] == llm.answer


class TestSessions:
    def test_lifecycle_and_isolation(self, llm):
        first, second = new_session(), new_session()
        client.post("/api/v1/chat", json={"query": QUESTION, "session_id": first})

        assert len(messages_of(first)) == 2
        assert messages_of(second) == []
        assert messages_of(first)[1]["citations"][0]["source_file"] == "崖州攻略.md"
        listed = {s["session_id"] for s in client.get("/api/v1/sessions").json()["sessions"]}
        assert {first, second} <= listed

        assert client.delete(f"/api/v1/sessions/{first}").status_code == 200
        assert client.get(f"/api/v1/sessions/{first}/messages").status_code == 404
        assert client.delete(f"/api/v1/sessions/{first}").status_code == 404
