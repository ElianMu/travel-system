"""知识问答接口。"""
from __future__ import annotations

import anyio
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.services import chat_service, session_service

router = APIRouter(tags=["chat"])

MAX_QUERY_LENGTH = 2000
# 停机时留给在途流式回答的时间，须小于 uvicorn 的 --timeout-graceful-shutdown（30 秒）
_SHUTDOWN_GRACE_SECONDS = 25


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)
    session_id: str | None = Field(default=None, max_length=64)


def _ensure_session_exists(session_id: str | None) -> None:
    if session_id and not session_service.session_exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")


@router.post("/chat")
def chat(req: ChatRequest) -> dict:
    """单轮/多轮问答（非流式）。"""
    _ensure_session_exists(req.session_id)
    return chat_service.chat(req.query, session_id=req.session_id)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> EventSourceResponse:
    """问答流式（SSE）。"""
    await run_in_threadpool(_ensure_session_exists, req.session_id)
    return EventSourceResponse(
        chat_service.chat_stream(req.query, req.session_id),
        shutdown_event=anyio.Event(),
        shutdown_grace_period=_SHUTDOWN_GRACE_SECONDS,
    )
