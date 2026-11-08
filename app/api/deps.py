"""接口依赖：API Key 轻量鉴权（对应 TDD §12.1）。"""
from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Header, HTTPException

from app.config import settings


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """校验 X-API-Key；未配置 API_KEY 时不启用（仅开发环境允许）。"""
    expected = settings.api_key
    if not expected:
        return
    if x_api_key is None or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="API Key 缺失或无效")
