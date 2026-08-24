"""LLM 生成 + 引用（对应 TDD §5.7）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.rag.prompts import SYSTEM_PROMPT, build_user_prompt

_client = None


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
        )
    return _client


def generate(query: str, context_hits: list[dict[str, Any]]) -> Answer:
    """基于检索片段生成答案，返回答案与引用。"""
    context = _format_context(context_hits)
    prompt = build_user_prompt(query, context)

    client = _get_client()
    resp = client.chat.completions.create(
        model=settings.deepseek_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        stream=False,
    )
    text = (resp.choices[0].message.content or "").strip()

    return Answer(text=text, citations=_build_citations(context_hits))


def _format_context(hits: list[dict[str, Any]]) -> str:
    """格式化检索片段为参考资料文本。"""
    parts = []
    for i, hit in enumerate(hits, 1):
        parts.append(f"[{i}] {hit.get('content', '')}")
    return "\n\n".join(parts)


def _build_citations(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从命中片段提取引用来源。"""
    return [
        {
            "source_file": hit.get("source_file", ""),
            "heading_path": hit.get("heading_path", ""),
            "score": hit.get("score"),
        }
        for hit in hits
    ]
