"""检索服务：景点/线路/实用信息检索（对应 TDD §5.8）。"""
from __future__ import annotations

from typing import Any

from app.rag.retriever import retrieve_with_fallback

CONTENT_TYPE_BY_INFO_TYPE = {
    "hotel": "酒店信息",
    "food": "美食介绍",
    "transport": "交通指南",
}


def search_attractions(
    query: str, region: str | None = None, top_k: int | None = None
) -> list[dict[str, Any]]:
    """景点检索。"""
    return retrieve_with_fallback(query, top_k=top_k, content_type="景点介绍", region=region)


def search_routes(
    query: str, region: str | None = None, top_k: int | None = None
) -> list[dict[str, Any]]:
    """线路检索。"""
    return retrieve_with_fallback(query, top_k=top_k, content_type="线路推荐", region=region)


def search_info(
    query: str, info_type: str = "hotel", top_k: int | None = None
) -> list[dict[str, Any]]:
    """实用信息检索（酒店/美食/交通）。"""
    content_type = CONTENT_TYPE_BY_INFO_TYPE[info_type]
    return retrieve_with_fallback(query, top_k=top_k, content_type=content_type)
