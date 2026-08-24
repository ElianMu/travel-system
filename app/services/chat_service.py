"""问答服务：检索 → 生成 → 返回答案与引用（对应 TDD §5.8）。"""
from __future__ import annotations

from typing import Any

from app.rag.generator import generate
from app.rag.retriever import retrieve


def chat(
    query: str, session_id: str | None = None, top_k: int = 5
) -> dict[str, Any]:
    """单轮问答（session_id 为多轮预留，S7 启用）。"""
    hits = retrieve(query, top_k=top_k)
    if not hits:
        return {"answer": "根据现有知识库无法回答。", "citations": []}

    answer = generate(query, hits)
    return {"answer": answer.text, "citations": answer.citations}
