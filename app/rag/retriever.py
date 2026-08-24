"""检索器：向量检索 + 元数据过滤 + 联网兜底（对应 TDD §5.6）。"""
from __future__ import annotations

from typing import Any

from app.rag.embedder import embed
from app.rag.store import get_vector_store


def retrieve(
    query: str,
    top_k: int = 5,
    content_type: str | None = None,
    region: str | None = None,
) -> list[dict[str, Any]]:
    """向量检索，支持 content_type / region 元数据过滤。"""
    store = get_vector_store()
    query_embedding = embed([query])[0]

    where = _build_where(content_type, region)
    result = store.query(query_embedding, top_k=top_k, where=where)
    return _parse_result(result)


def _build_where(
    content_type: str | None, region: str | None
) -> dict[str, Any] | None:
    """构造 chromadb 元数据过滤条件。"""
    conditions: list[dict[str, Any]] = []
    if content_type:
        conditions.append({"content_type": content_type})
    if region:
        conditions.append({"region": region})
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _parse_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    """解析 chromadb 查询结果为标准 hit 列表。"""
    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0] if result.get("distances") else None

    hits: list[dict[str, Any]] = []
    for i, doc_id in enumerate(ids):
        hit: dict[str, Any] = {"id": doc_id}
        if i < len(documents):
            hit["content"] = documents[i]
        if i < len(metadatas) and metadatas[i]:
            hit.update(metadatas[i])
        if distances and i < len(distances) and distances[i] is not None:
            hit["score"] = round(1 - distances[i], 4)  # cosine 距离 → 相似度
        hits.append(hit)
    return hits
