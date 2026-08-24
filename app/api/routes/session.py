"""会话接口。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services import session_service

router = APIRouter(tags=["session"])


@router.get("/sessions")
def list_sessions() -> dict:
    """会话列表。"""
    return {"sessions": session_service.list_sessions()}


@router.post("/sessions")
def create_session(title: str | None = None) -> dict:
    """创建会话。"""
    return session_service.create_session(title)


@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: str) -> dict:
    """会话消息。"""
    return {"messages": session_service.get_messages(session_id)}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict:
    """删除会话。"""
    if not session_service.delete_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}
