"""景文智核 · 智能旅游知识库系统 — 应用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import import_
from app.config import settings
from app.models import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表。"""
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

# 后续阶段挂载路由：search / chat / session
