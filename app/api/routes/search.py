"""检索接口。"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from app.models import Chunk, Document, SessionLocal
from app.services import search_service

router = APIRouter(tags=["search"])

SearchQuery = Annotated[str, Query(min_length=1, max_length=500)]
TopK = Annotated[int | None, Query(ge=1, le=20)]


@router.get("/search/attractions")
def attractions(query: SearchQuery, city: str | None = None, top_k: TopK = None) -> dict:
    """景点检索。"""
    return {"results": search_service.search_attractions(query, region=city, top_k=top_k)}


@router.get("/search/routes")
def routes(query: SearchQuery, region: str | None = None, top_k: TopK = None) -> dict:
    """线路检索。"""
    return {"results": search_service.search_routes(query, region=region, top_k=top_k)}


@router.get("/search/info")
def info(
    query: SearchQuery,
    type: Literal["hotel", "food", "transport"] = "hotel",
    top_k: TopK = None,
) -> dict:
    """实用信息检索（hotel/food/transport）。"""
    return {"results": search_service.search_info(query, info_type=type, top_k=top_k)}


@router.get("/documents")
def documents(
    content_type: str | None = None,
    region: str | None = None,
    name: str | None = None,
    source_file: str | None = None,
) -> dict:
    """元数据列表，支持 content_type/region/name/source_file 筛选（后三者为模糊匹配）。"""
    db = SessionLocal()
    q = db.query(Document)
    if content_type:
        q = q.filter(Document.content_type == content_type)
    if region:
        q = q.filter(Document.region.contains(region, autoescape=True))
    if name:
        q = q.filter(Document.name.contains(name, autoescape=True))
    if source_file:
        q = q.filter(Document.source_file.contains(source_file, autoescape=True))
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


@router.get("/documents/{doc_id}")
def document_detail(doc_id: int) -> dict:
    """文档详情（元数据 + 片段列表）。"""
    db = SessionLocal()
    doc = db.get(Document, doc_id)
    if doc is None:
        db.close()
        raise HTTPException(status_code=404, detail="文档不存在")
    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == doc_id)
        .order_by(Chunk.chunk_index)
        .all()
    )
    result = {
        "id": doc.id,
        "source_file": doc.source_file,
        "source_path": doc.source_path,
        "content_type": doc.content_type,
        "region": doc.region,
        "name": doc.name,
        "theme": doc.theme,
        "status": doc.status,
        "chunks": [
            {"chunk_index": c.chunk_index, "heading_path": c.heading_path, "content": c.content}
            for c in chunks
        ],
    }
    db.close()
    return result


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int) -> dict:
    """删除文档（元数据 + 片段 + 向量）。"""
    db = SessionLocal()
    doc = db.get(Document, doc_id)
    if doc is None:
        db.close()
        raise HTTPException(status_code=404, detail="文档不存在")
    db.query(Chunk).filter(Chunk.document_id == doc_id).delete()
    db.delete(doc)
    db.commit()
    db.close()

    from app.rag.store import get_vector_store

    get_vector_store().delete_by_document(doc_id)
    return {"ok": True}
