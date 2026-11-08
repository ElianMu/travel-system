"""检索服务：景点/线路/实用信息检索（对应 TDD §5.8）。"""
from __future__ import annotations

import re
from typing import Any

from app.rag.retriever import retrieve_with_fallback
from app.rag.store import get_vector_store

CONTENT_TYPE_BY_INFO_TYPE = {
    "hotel": "酒店信息",
    "food": "美食介绍",
    "transport": "交通指南",
}

# 结构化字段 → 文档 H2 章节名（对应 FR-ATTR-002、FR-ROUTE-001、FR-INFO-001/002）。
# 文档没有对应章节时字段留空，不做推断，避免编造时间、价格类信息。
_INFO_FIELDS = {
    "详细信息": "目的地概览",
    "实用 tips": "常见决策点",
    "适合人群": "适合人群",
    "最佳游览季节": "最佳游览季节",
}
_DETAIL_FIELDS = {
    "景点介绍": {
        "景区特色": "目的地概览",
        "适合人群": "适合人群",
        "最佳游览时间": "最佳游览时间",
        "建议停留时长": "建议停留时长",
    },
    "线路推荐": {
        "预算参考": "预算参考",
        "适合人群": "适合人群",
        "建议停留时长": "建议停留时长",
    },
    "酒店信息": _INFO_FIELDS,
    "美食介绍": _INFO_FIELDS,
    "交通指南": _INFO_FIELDS,
}
_DETAIL_MAX_CHARS = 300
_NUMBER = r"[\d一二两三四五六七八九十]+"
_TRIP_DAYS = re.compile(rf"{_NUMBER}(?:\s*至\s*{_NUMBER})?\s*[日天]")


def _section_text(chunks: list[tuple[str, str]], heading: str) -> str:
    """提取某 H2 章节的纯文本（章节可能被切分为多个 H3 片段）。"""
    parts = [
        text for path, text in chunks if path == heading or path.startswith(f"{heading} > ")
    ]
    text = re.sub(rf"^##\s*{re.escape(heading)}\s*$", "", "\n".join(parts), flags=re.M)
    return re.sub(r"^#+\s*", "", text, flags=re.M).strip()[:_DETAIL_MAX_CHARS]


def _attach_details(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """为本地命中附加所属文档的结构化字段；联网结果无章节，details 为空。"""
    store = get_vector_store()
    chunks_by_document: dict[int, list[tuple[str, str]]] = {}
    for hit in hits:
        document_id = hit.get("document_id")
        if document_id is None:
            hit["details"] = {}
            continue
        if document_id not in chunks_by_document:
            chunks_by_document[document_id] = store.get_document_chunks(document_id)
        chunks = chunks_by_document[document_id]
        fields = _DETAIL_FIELDS.get(hit.get("content_type"), {})
        details = {label: _section_text(chunks, heading) for label, heading in fields.items()}
        if hit.get("content_type") == "线路推荐":
            days = _TRIP_DAYS.search(hit.get("name") or "")
            details = {"行程天数": days.group() if days else "", **details}
        hit["details"] = details
    return hits


def search_attractions(
    query: str, region: str | None = None, top_k: int | None = None
) -> list[dict[str, Any]]:
    """景点检索。"""
    return _attach_details(
        retrieve_with_fallback(query, top_k=top_k, content_type="景点介绍", region=region)
    )


def search_routes(
    query: str, region: str | None = None, top_k: int | None = None
) -> list[dict[str, Any]]:
    """线路检索。"""
    return _attach_details(
        retrieve_with_fallback(query, top_k=top_k, content_type="线路推荐", region=region)
    )


def search_info(
    query: str, info_type: str = "hotel", top_k: int | None = None
) -> list[dict[str, Any]]:
    """实用信息检索（酒店/美食/交通）。"""
    content_type = CONTENT_TYPE_BY_INFO_TYPE[info_type]
    return _attach_details(retrieve_with_fallback(query, top_k=top_k, content_type=content_type))
