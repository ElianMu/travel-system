"""API Key 鉴权（TDD §12.1）。"""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, settings
from app.main import app

client = TestClient(app)
# 校验通过后会因缺少必填参数返回 422，无需依赖数据库即可证明鉴权已放行
PROTECTED = "/api/v1/search/attractions"


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret-key")
    return "secret-key"


def test_disabled_when_not_configured():
    assert client.get(PROTECTED).status_code == 422


@pytest.mark.usefixtures("api_key")
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}, {"X-API-Key": ""}])
def test_rejects_missing_or_wrong_key(headers):
    resp = client.get(PROTECTED, headers=headers)
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == "UNAUTHORIZED" and body["trace_id"]


def test_accepts_correct_key(api_key):
    assert client.get(PROTECTED, headers={"X-API-Key": api_key}).status_code == 422


@pytest.mark.usefixtures("api_key")
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/v1/import"),
        ("get", "/api/v1/import/tasks/1"),
        ("get", "/api/v1/documents"),
        ("delete", "/api/v1/documents/1"),
        ("post", "/api/v1/chat"),
        ("post", "/api/v1/chat/stream"),
        ("get", "/api/v1/sessions"),
    ],
)
def test_all_business_routes_are_protected(method, path):
    assert getattr(client, method)(path).status_code == 401


@pytest.mark.usefixtures("api_key")
@pytest.mark.parametrize("path", ["/health", "/metrics"])
def test_system_routes_stay_open(path):
    assert client.get(path).status_code == 200


def test_prod_requires_api_key():
    with pytest.raises(ValidationError, match="API_KEY"):
        Settings(_env_file=None, app_env="prod", deepseek_api_key="k", api_key="")
