"""检索接口。"""
from __future__ import annotations

from fastapi import APIRouter

from app.models import Document, SessionLocal
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


@router.get("/documents")
def documents(
    content_type: str | None = None,
    region: str | None = None,
    name: str | None = None,
) -> dict:
    """元数据列表，支持 content_type/region/name 筛选。"""
    db = SessionLocal()
    q = db.query(Document)
    if content_type:
        q = q.filter(Document.content_type == content_type)
    if region:
        q = q.filter(Document.region == region)
    if name:
        q = q.filter(Document.name == name)
    docs = q.order_by(Document.id.desc()).limit(200).all()
    result = [
        {
            "id": d.id,
            "source_file": d.source_file,
            "content_type": d.content_type,
            "region": d.region,
            "name": d.name,
            "theme": d.theme,
            "status": d.status,
        }
        for d in docs
    ]
    db.close()
    return {"documents": result}
