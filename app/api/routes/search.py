"""检索接口。"""
from __future__ import annotations

from fastapi import APIRouter

from app.services import search_service

router = APIRouter(tags=["search"])


@router.get("/search/attractions")
def attractions(query: str, city: str | None = None, top_k: int = 5) -> dict:
    """景点检索。"""
    return {"results": search_service.search_attractions(query, region=city, top_k=top_k)}


@router.get("/search/routes")
def routes(query: str, region: str | None = None, top_k: int = 5) -> dict:
    """线路检索。"""
    return {"results": search_service.search_routes(query, region=region, top_k=top_k)}


@router.get("/search/info")
def info(query: str, type: str = "hotel", top_k: int = 5) -> dict:
    """实用信息检索（hotel/food/transport）。"""
    return {"results": search_service.search_info(query, info_type=type, top_k=top_k)}
