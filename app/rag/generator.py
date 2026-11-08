"""LLM 生成 + 引用 + 查询改写（对应 TDD §5.7、§7.2）。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator

from app.config import settings
from app.core.observability import tracer
from app.core.resilience import call_with_resilience, llm_breaker, record_external_failure
from app.rag.prompts import QUERY_REWRITE_PROMPT, SYSTEM_PROMPT, build_user_prompt

_client = None
_EXCERPT_LENGTH = 120


@dataclass
class Answer:
    """问答结果。"""

    text: str
    citations: list[dict[str, Any]]


def _get_client():
    """延迟初始化 OpenAI 兼容客户端（DeepSeek）。"""
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI(
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,  # 重试统一由 call_with_resilience 负责
        )
    return _client


def _complete(**kwargs: Any) -> str:
    """调用 LLM（超时、重试、熔断），返回文本。"""

    def create() -> str:
        resp = _get_client().chat.completions.create(model=settings.deepseek_model, **kwargs)
        return (resp.choices[0].message.content or "").strip()

    with tracer.start_as_current_span("llm.complete"):
        return call_with_resilience(llm_breaker, create)


def generate(query: str, context_hits: list[dict[str, Any]]) -> Answer:
    """基于检索片段生成答案，返回答案与引用。"""
    context = _format_context(context_hits)
    prompt = build_user_prompt(query, context)

    text = _complete(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        stream=False,
    )

    return Answer(text=text, citations=build_citations(context_hits))


async def stream_generate(
    query: str, context_hits: list[dict[str, Any]]
) -> AsyncIterator[str]:
    """流式生成，逐 token yield（异步 httpx，避免与 torch 原生库冲突）。

    失败不在此重试：由调用方降级为带重试的非流式调用。
    """
    import httpx

    llm_breaker.before_call()

    context = _format_context(context_hits)
    prompt = build_user_prompt(query, context)
    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "stream": True,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            async with client.stream(
                "POST",
                url,
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    if data.get("choices"):
                        delta = data["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
    except Exception as exc:
        record_external_failure(llm_breaker, exc)
        raise
    llm_breaker.record_success()


def rewrite_query(question: str, history: list[dict[str, Any]]) -> str:
    """多轮查询改写（结合历史补全指代）。"""
    history_text = _format_history(history)
    prompt = QUERY_REWRITE_PROMPT.format(history=history_text, question=question)

    rewritten = _complete(messages=[{"role": "user", "content": prompt}], temperature=0)
    return rewritten or question


def build_citations(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从命中片段提取引用来源。"""
    return [
        {
            "source_file": hit.get("source_file", ""),
            "heading_path": hit.get("heading_path", ""),
            "chunk_id": hit.get("id", ""),
            "excerpt": hit.get("content", "")[:_EXCERPT_LENGTH],
            "score": hit.get("score"),
        }
        for hit in hits
    ]


def _format_context(hits: list[dict[str, Any]]) -> str:
    """格式化检索片段为参考资料文本，带来源以便模型按要求列出引用。"""
    parts = []
    for i, hit in enumerate(hits, 1):
        source = hit.get("source_file", "")
        heading = hit.get("heading_path", "")
        label = f"{source}（{heading}）" if heading else source
        parts.append(f"[{i}] 来源：{label}\n{hit.get('content', '')}")
    return "\n\n".join(parts)


def _format_history(history: list[dict[str, Any]]) -> str:
    """格式化对话历史（最近 6 条）。"""
    parts = []
    for m in history[-6:]:
        role = "用户" if m.get("role") == "user" else "助手"
        parts.append(f"{role}：{m.get('content', '')}")
    return "\n".join(parts)
