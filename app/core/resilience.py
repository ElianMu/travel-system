"""外部调用稳定性：指数退避重试与熔断（对应 TDD §12.2）。"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, TypeVar

from app.core.observability import EXTERNAL_CALL_ERRORS

logger = logging.getLogger(__name__)

T = TypeVar("T")

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 1.0
FAILURE_THRESHOLD = 5
RECOVERY_SECONDS = 30.0
_RETRYABLE_CLIENT_STATUS = {408, 409, 429}


class ExternalServiceError(RuntimeError):
    """外部依赖调用失败（重试耗尽或不可重试）。"""

    def __init__(self, service: str, reason: str = "调用失败") -> None:
        super().__init__(f"{service} {reason}")
        self.service = service


class CircuitOpenError(ExternalServiceError):
    """熔断器打开，短时间内拒绝调用。"""

    def __init__(self, service: str) -> None:
        super().__init__(service, "已熔断，暂时拒绝调用")


class CircuitBreaker:
    """连续失败达到阈值后打开；冷却期过后放行试探调用，成功即恢复。"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = FAILURE_THRESHOLD,
        recovery_seconds: float = RECOVERY_SECONDS,
    ) -> None:
        self.name = name
        self._failure_threshold = failure_threshold
        self._recovery_seconds = recovery_seconds
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at: float | None = None

    def before_call(self) -> None:
        with self._lock:
            if self._opened_at is None:
                return
            if time.monotonic() - self._opened_at < self._recovery_seconds:
                raise CircuitOpenError(self.name)

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self._failure_threshold:
                if self._opened_at is None:
                    logger.error("熔断器打开 service=%s", self.name)
                self._opened_at = time.monotonic()

    def reset(self) -> None:
        self.record_success()


llm_breaker = CircuitBreaker("llm")
embedding_breaker = CircuitBreaker("embedding")
web_search_breaker = CircuitBreaker("web_search")


def is_retryable(exc: Exception) -> bool:
    """超时、连接错误、限流与 5xx 可重试；其余 4xx（如密钥错误）重试无意义。"""
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    return status is None or status >= 500 or status in _RETRYABLE_CLIENT_STATUS


def record_external_failure(breaker: CircuitBreaker, exc: Exception) -> None:
    """记录一次外部调用失败；不可重试的错误不代表服务异常，不计入熔断。"""
    EXTERNAL_CALL_ERRORS.labels(breaker.name).inc()
    if is_retryable(exc):
        breaker.record_failure()


def call_with_resilience(
    breaker: CircuitBreaker,
    func: Callable[[], T],
    attempts: int = MAX_ATTEMPTS,
    base_delay: float = BASE_DELAY_SECONDS,
) -> T:
    """带熔断与指数退避重试地执行外部调用。"""
    for attempt in range(attempts):
        breaker.before_call()
        try:
            result = func()
        except Exception as exc:  # noqa: BLE001
            record_external_failure(breaker, exc)
            if not is_retryable(exc) or attempt == attempts - 1:
                raise ExternalServiceError(breaker.name) from exc
            logger.warning("外部调用失败，准备重试 service=%s attempt=%d", breaker.name, attempt + 1)
            time.sleep(base_delay * 2**attempt)
        else:
            breaker.record_success()
            return result
    raise AssertionError("attempts 必须大于 0")
