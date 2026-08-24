"""景文智核 · 智能旅游知识库系统 — 应用入口。"""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.api.routes import chat, import_, search, session
from app.config import settings
from app.core.logging import setup_logging, trace_id_var
from app.models import init_db

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：预热 Embedding 模型 + 建表。

    预热必须在任何数据库操作之前：torch 模型在 pymysql 连接后首次加载会在
    Windows 下触发原生库冲突（段错误），先加载模型即可规避。
    """
    from app.rag.embedder import embed

    embed(["预热"])  # 加载本地 bge 模型，缓存复用
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="面向旅游场景的检索增强生成（RAG）知识库系统",
    lifespan=lifespan,
)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """为每个请求注入 trace_id，贯通结构化日志。"""
    trace_id = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:16]
    trace_id_var.set(trace_id)
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.get("/health", tags=["system"])
def health() -> dict:
    """健康检查。"""
    return {"status": "ok", "service": settings.app_name}


app.include_router(import_.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(session.router, prefix="/api/v1")
