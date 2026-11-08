"""检索器：向量检索 + 元数据过滤 + 联网兜底（对应 TDD §5.6）。"""
from __future__ import annotations

from typing import Any

from app.config import settings
from app.rag import web_search
from app.rag.embedder import embed
from app.rag.store import get_vector_store


def retrieve(
    query: str,
    top_k: int | None = None,
    content_type: str | None = None,
    region: str | None = None,
) -> list[dict[str, Any]]:
    """向量检索，支持 content_type / region 元数据过滤。"""
    store = get_vector_store()
    query_embedding = embed([query])[0]

    where = _build_where(content_type, region)
    result = store.query(query_embedding, top_k=top_k or settings.retrieve_top_k, where=where)
    return _parse_result(result)


def retrieve_with_fallback(
    query: str,
    top_k: int | None = None,
    content_type: str | None = None,
    region: str | None = None,
) -> list[dict[str, Any]]:
    """本地检索优先；本地无命中或相关度不足时转联网搜索兜底。"""
    hits = [
        hit
        for hit in retrieve(query, top_k=top_k, content_type=content_type, region=region)
        if hit.get("score", 0) >= settings.retrieve_min_score
    ]
    if hits:
        return hits

    web_query = f"{region} {query}" if region else query
    results = web_search.search(web_query, max_results=top_k or settings.retrieve_top_k)
    return [_web_hit(item, content_type, region) for item in results]


def _web_hit(
    item: dict[str, Any], content_type: str | None, region: str | None
) -> dict[str, Any]:
    """联网结果转为与本地命中一致的结构。"""
    return {
        "id": item["url"],
        "content": item["content"],
        "name": item["title"],
        "content_type": content_type or "联网结果",
        "region": region or "",
        "theme": "",
        "heading_path": item["title"],
        "source_file": item["url"],
        "score": None,
        "source": "web",
    }


def _build_where(
    content_type: str | None, region: str | None
) -> dict[str, Any] | None:
    """构造元数据过滤条件；region 用子串匹配（如「昆明、大理、丽江」可被「大理」命中）。"""
    conditions: list[dict[str, Any]] = []
    if content_type:
        conditions.append({"content_type": content_type})
    if region:
        conditions.append({"region": {"$contains": region}})
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _parse_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    """解析向量库查询结果为标准 hit 列表。"""
    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0] if result.get("distances") else None

    hits: list[dict[str, Any]] = []
    for i, doc_id in enumerate(ids):
        hit: dict[str, Any] = {"id": doc_id, "source": "local"}
        if i < len(documents):
            hit["content"] = documents[i]
        if i < len(metadatas) and metadatas[i]:
            hit.update(metadatas[i])
        if distances and i < len(distances) and distances[i] is not None:
            hit["score"] = round(1 - distances[i], 4)  # cosine 距离 → 相似度
        hits.append(hit)
    return hits
