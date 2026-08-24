"""会话服务：会话与历史消息管理（对应 TDD §5.8）。"""
from __future__ import annotations

import json
import uuid
from typing import Any

from app.models import Message, Session, SessionLocal


def create_session(title: str | None = None) -> dict[str, Any]:
    """创建会话，返回会话信息。"""
    db = SessionLocal()
    session = Session(session_id=uuid.uuid4().hex, title=title or "新对话")
    db.add(session)
    db.commit()
    db.refresh(session)
    result = {"session_id": session.session_id, "title": session.title}
    db.close()
    return result


def list_sessions() -> list[dict[str, Any]]:
    """列出所有会话（按创建时间倒序）。"""
    db = SessionLocal()
    sessions = db.query(Session).order_by(Session.id.desc()).all()
    result = [
        {
            "session_id": s.session_id,
            "title": s.title,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]
    db.close()
    return result


def get_messages(session_id: str) -> list[dict[str, Any]]:
    """查询会话消息（按时间正序）。"""
    db = SessionLocal()
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id)
        .all()
    )
    result = []
    for m in messages:
        result.append(
            {
                "role": m.role,
                "content": m.content,
                "citations": json.loads(m.citations) if m.citations else [],
            }
        )
    db.close()
    return result


def add_message(
    session_id: str, role: str, content: str, citations: list | None = None
) -> None:
    """记录一条消息。"""
    db = SessionLocal()
    msg = Message(
        session_id=session_id,
        role=role,
        content=content,
        citations=json.dumps(citations or [], ensure_ascii=False),
    )
    db.add(msg)
    db.commit()
    db.close()


def delete_session(session_id: str) -> bool:
    """删除会话及其消息。"""
    db = SessionLocal()
    session = db.query(Session).filter(Session.session_id == session_id).first()
    if session is None:
        db.close()
        return False
    db.query(Message).filter(Message.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    db.close()
    return True
