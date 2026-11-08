"""可观测性：Prometheus 指标与 OpenTelemetry 链路追踪（对应 TDD §12.3）。"""
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prometheus_client import Counter, Histogram

from app.config import settings

IMPORT_TASKS = Counter("jwzh_import_tasks_total", "导入任务数", ["status"])
RETRIEVE_LATENCY = Histogram("jwzh_retrieve_latency_seconds", "向量检索延迟")
FIRST_TOKEN_LATENCY = Histogram("jwzh_first_token_latency_seconds", "流式问答首 Token 延迟")
EXTERNAL_CALL_ERRORS = Counter("jwzh_external_call_errors_total", "外部调用错误数", ["service"])
HTTP_REQUESTS = Counter("jwzh_http_requests_total", "HTTP 请求数", ["method", "status"])

tracer = trace.get_tracer("jingwen-zhihui")


def setup_tracing() -> None:
    """初始化链路追踪；OTEL_CONSOLE_EXPORT=true 时把 Span 输出到控制台。"""
    provider = TracerProvider(resource=Resource.create({"service.name": "jingwen-zhihui"}))
    if settings.otel_console_export:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
