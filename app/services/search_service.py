"""检索服务：景点/线路/实用信息检索（对应 TDD §5.8）。"""
from __future__ import annotations

from typing import Any

from app.rag.retriever import retrieve

_CONTENT_TYPE_MAP = {
    "hotel": "酒店信息",
    "food": "美食介绍",
    "transport": "交通指南",
}


def search_attractions(
    query: str, region: str | None = None, top_k: int = 5
) -> list[dict[str, Any]]:
    """景点检索。"""
    return retrieve(query, top_k=top_k, content_type="景点介绍", region=region)


def search_routes(
    query: str, region: str | None = None, top_k: int = 5
) -> list[dict[str, Any]]:
    """线路检索。"""
    return retrieve(query, top_k=top_k, content_type="线路推荐", region=region)


def search_info(
    query: str, info_type: str = "hotel", top_k: int = 5
) -> list[dict[str, Any]]:
    """实用信息检索（酒店/美食/交通）。"""
    content_type = _CONTENT_TYPE_MAP.get(info_type, "酒店信息")
    return retrieve(query, top_k=top_k, content_type=content_type)
