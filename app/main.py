"""景文智核 · 智能旅游知识库系统 — 应用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import chat, import_, search, session
from app.config import settings
from app.models import init_db


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


@app.get("/health", tags=["system"])
def health() -> dict:
    """健康检查。"""
    return {"status": "ok", "service": settings.app_name}


app.include_router(import_.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(session.router, prefix="/api/v1")
