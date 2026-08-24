"""景文智核 · 智能旅游知识库系统 — 应用入口。"""
from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="面向旅游场景的检索增强生成（RAG）知识库系统",
)


@app.get("/health", tags=["system"])
def health() -> dict:
    """健康检查。"""
    return {"status": "ok", "service": settings.app_name}


# 后续阶段在此挂载路由：import / search / chat / session
