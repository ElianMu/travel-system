"""景文智核 · 智能旅游知识库系统 — 应用入口。"""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes import chat, import_, search, session
from app.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import setup_logging, trace_id_var
from app.core.observability import HTTP_REQUESTS, setup_tracing, tracer
from app.models import engine, init_db

setup_logging()
setup_tracing()

logger = logging.getLogger(__name__)

_MAX_TRACE_ID_LENGTH = 64


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：预热 Embedding 模型 + 建表；停机时释放数据库连接。

    预热必须在任何数据库操作之前：torch 模型在 pymysql 连接后首次加载会在
    Windows 下触发原生库冲突（段错误），先加载模型即可规避。

    收到 SIGTERM 时 uvicorn 先停止接收新连接并等待在途请求，随后执行 yield 之后的清理。
    """
    from app.rag.embedder import embed

    embed(["预热"])  # 加载本地 bge 模型，缓存复用
    init_db()
    logger.info("服务启动完成 env=%s", settings.app_env)
    yield
    engine.dispose()
    logger.info("服务已优雅停机")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="面向旅游场景的检索增强生成（RAG）知识库系统",
    lifespan=lifespan,
)
register_exception_handlers(app)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """为每个请求注入 trace_id，贯通结构化日志与链路追踪。"""
    trace_id = (request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:16])[:_MAX_TRACE_ID_LENGTH]
    trace_id_var.set(trace_id)
    started = time.perf_counter()
    with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
        span.set_attribute("app.trace_id", trace_id)
        response = await call_next(request)
        span.set_attribute("http.status_code", response.status_code)
    response.headers["X-Trace-Id"] = trace_id
    HTTP_REQUESTS.labels(request.method, str(response.status_code)).inc()
    logger.info(
        "request",
        extra={
            "fields": {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            }
        },
    )
    return response


@app.get("/health", tags=["system"])
def health() -> dict:
    """健康检查。"""
    return {"status": "ok", "service": settings.app_name}


@app.get("/metrics", tags=["system"], include_in_schema=False)
def metrics() -> Response:
    """Prometheus 指标。"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(import_.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(session.router, prefix="/api/v1")
