"""统一错误响应：{"code", "message", "trace_id"}（对应 TDD §14）。"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.logging import get_trace_id
from app.core.resilience import ExternalServiceError

logger = logging.getLogger(__name__)

_CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "trace_id": get_trace_id()},
    )


async def _handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
    code = _CODE_BY_STATUS.get(exc.status_code, "HTTP_ERROR")
    return _error(exc.status_code, code, str(exc.detail))


async def _handle_validation_error(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first["loc"][1:])
    return _error(422, "INVALID_REQUEST", f"参数不合法：{field}（{first['msg']}）")


async def _handle_external_error(_request: Request, exc: ExternalServiceError) -> JSONResponse:
    logger.error("外部依赖不可用 service=%s", exc.service, exc_info=exc)
    return _error(503, f"{exc.service.upper()}_UNAVAILABLE", "依赖服务暂不可用，请稍后重试")


async def _handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
    logger.error("未处理异常", exc_info=exc)
    return _error(500, "INTERNAL_ERROR", "服务内部错误")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(ExternalServiceError, _handle_external_error)
    app.add_exception_handler(Exception, _handle_unexpected)
