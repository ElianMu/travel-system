"""问答服务：检索 → 生成 → 返回答案与引用（对应 TDD §5.8）。"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from app.rag import generator
from app.rag.retriever import retrieve
from app.services import session_service


def chat(query: str, session_id: str | None = None, top_k: int = 5) -> dict[str, Any]:
    """单轮/多轮问答（非流式）。"""
    rewrite = _maybe_rewrite(query, session_id)
    hits = retrieve(rewrite, top_k=top_k)

    if not hits:
        answer_text, citations = "根据现有知识库无法回答。", []
    else:
        answer = generator.generate(query, hits)
        answer_text, citations = answer.text, answer.citations

    _record(session_id, query, answer_text, citations)
    return {"answer": answer_text, "citations": citations}


async def chat_stream(
    query: str, session_id: str | None = None, top_k: int = 5
) -> AsyncIterator[dict[str, Any]]:
    """流式问答：SSE 事件流，异常降级为非流式。"""
    try:
        rewrite = _maybe_rewrite(query, session_id)
        hits = retrieve(rewrite, top_k=top_k)

        if not hits:
            yield _sse("token", {"delta": "根据现有知识库无法回答。"})
            yield _sse("done", {"citations": []})
            return

        citations = generator.build_citations(hits)
        full_text = ""
        async for delta in generator.stream_generate(query, hits):
            full_text += delta
            yield _sse("token", {"delta": delta})

        yield _sse("done", {"citations": citations})
        _record(session_id, query, full_text, citations)
    except Exception:  # noqa: BLE001  流式失败降级为非流式
        result = chat(query, session_id, top_k)
        yield _sse("message", {"answer": result["answer"]})
        yield _sse("done", {"citations": result["citations"]})


def _maybe_rewrite(query: str, session_id: str | None) -> str:
    """多轮场景下做查询改写。"""
    if not session_id:
        return query
    history = session_service.get_messages(session_id)
    if not history:
        return query
    return generator.rewrite_query(query, history)


def _record(
    session_id: str | None,
    query: str,
    answer: str,
    citations: list[dict[str, Any]],
) -> None:
    """记录一轮对话（用户 + 助手）。"""
    if not session_id:
        return
    session_service.add_message(session_id, "user", query)
    session_service.add_message(session_id, "assistant", answer, citations)


def _sse(event: str, data: dict[str, Any]) -> dict[str, Any]:
    """构造 SSE 事件。"""
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}
