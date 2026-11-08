"""重试与熔断单元测试（S8 验收）。"""
from types import SimpleNamespace

import pytest

from app.core.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    ExternalServiceError,
    call_with_resilience,
    is_retryable,
)


def failing(exc):
    def call():
        call.count += 1
        raise exc

    call.count = 0
    return call


def status_error(status):
    error = RuntimeError("http")
    error.status_code = status
    return error


def test_retries_then_succeeds():
    outcomes = iter([TimeoutError(), TimeoutError(), "ok"])

    def flaky():
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    assert call_with_resilience(CircuitBreaker("t"), flaky, base_delay=0) == "ok"


def test_gives_up_after_three_attempts():
    call = failing(TimeoutError())
    with pytest.raises(ExternalServiceError):
        call_with_resilience(CircuitBreaker("t"), call, base_delay=0)
    assert call.count == 3


def test_auth_error_is_not_retried_and_does_not_open_circuit():
    call = failing(status_error(401))
    breaker = CircuitBreaker("t", failure_threshold=1)
    with pytest.raises(ExternalServiceError):
        call_with_resilience(breaker, call, base_delay=0)
    assert call.count == 1
    breaker.before_call()  # 未熔断


def test_circuit_opens_and_rejects_without_calling():
    breaker = CircuitBreaker("t", failure_threshold=2, recovery_seconds=60)
    with pytest.raises(ExternalServiceError):
        call_with_resilience(breaker, failing(TimeoutError()), attempts=2, base_delay=0)

    guarded = failing(TimeoutError())
    with pytest.raises(CircuitOpenError):
        call_with_resilience(breaker, guarded, base_delay=0)
    assert guarded.count == 0


def test_circuit_recovers_after_cooldown():
    breaker = CircuitBreaker("t", failure_threshold=1, recovery_seconds=0)
    with pytest.raises(ExternalServiceError):
        call_with_resilience(breaker, failing(TimeoutError()), attempts=1)
    assert call_with_resilience(breaker, lambda: "ok") == "ok"


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (TimeoutError(), True),
        (status_error(429), True),
        (status_error(503), True),
        (status_error(400), False),
        (SimpleNamespace(response=SimpleNamespace(status_code=401)), False),
    ],
)
def test_is_retryable(exc, expected):
    assert is_retryable(exc) is expected
