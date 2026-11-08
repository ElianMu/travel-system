"""问答服务：检索 → 生成 → 返回答案与引用（对应 TDD §5.8）。"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator

from app.core.observability import FIRST_TOKEN_LATENCY
from app.rag import generator
from app.rag.retriever import retrieve_with_fallback
from app.services import session_service

logger = logging.getLogger(__name__)

NO_ANSWER_TEXT = "根据现有知识库无法回答。"


def chat(query: str, session_id: str | None = None, top_k: int | None = None) -> dict[str, Any]:
    """单轮/多轮问答（非流式）。"""
    standalone_query = _maybe_rewrite(query, session_id)
    hits = retrieve_with_fallback(standalone_query, top_k=top_k)

    if not hits:
        answer_text, citations = NO_ANSWER_TEXT, []
    else:
        # 用改写后的问题生成，否则「那里的美食呢」这类追问模型无从理解
        answer = generator.generate(standalone_query, hits)
        answer_text, citations = answer.text, answer.citations

    _record(session_id, query, answer_text, citations)
    return {"answer": answer_text, "citations": citations}


async def chat_stream(
    query: str, session_id: str | None = None, top_k: int | None = None
) -> AsyncIterator[dict[str, Any]]:
    """流式问答：SSE 事件流，异常降级为非流式。"""
    full_text = ""
    citations: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        # 改写与向量检索是同步调用，放到线程池以免阻塞事件循环
        standalone_query = await asyncio.to_thread(_maybe_rewrite, query, session_id)
        hits = await asyncio.to_thread(retrieve_with_fallback, standalone_query, top_k)

        if not hits:
            full_text = NO_ANSWER_TEXT
            yield _sse("token", {"delta": full_text})
        else:
            citations = generator.build_citations(hits)
            async for delta in generator.stream_generate(standalone_query, hits):
                if not full_text:
                    FIRST_TOKEN_LATENCY.observe(time.perf_counter() - started)
                full_text += delta
                yield _sse("token", {"delta": delta})
            if not full_text:
                raise RuntimeError("LLM 流式响应为空")
    except Exception:  # noqa: BLE001  流式失败降级为非流式
        logger.warning("流式问答失败，降级为非流式", exc_info=True)
        try:
            result = await asyncio.to_thread(chat, query, session_id, top_k)
        except Exception:  # noqa: BLE001
            logger.exception("非流式问答同样失败")
            yield _sse("error", {"message": "问答服务暂不可用，请稍后重试"})
            return
        yield _sse("message", {"answer": result["answer"]})
        yield _sse("done", {"citations": result["citations"]})
        return

    try:
        await asyncio.to_thread(_record, session_id, query, full_text, citations)
    except Exception:  # noqa: BLE001  答案已送达，历史写入失败不影响本次回答
        logger.exception("会话消息写入失败 session_id=%s", session_id)
    yield _sse("done", {"citations": citations})


def _maybe_rewrite(query: str, session_id: str | None) -> str:
    """多轮场景下做查询改写。"""
    if not session_id:
        return query
    history = session_service.get_messages(session_id)
    if not history:
        return query
    try:
        return generator.rewrite_query(query, history)
    except Exception:  # noqa: BLE001  改写失败退回原问题，不阻断问答
        logger.warning("查询改写失败，使用原问题", exc_info=True)
        return query


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
