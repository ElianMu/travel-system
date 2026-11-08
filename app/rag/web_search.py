"""联网搜索：Tavily Search API 兜底（对应 TDD §5.6）。"""
from __future__ import annotations

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def search(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """调用 Tavily 联网搜索；未配置 key 或失败时返回空列表（不阻断主流程）。"""
    if not settings.tavily_api_key:
        return []

    import requests

    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
            json={"query": query, "max_results": max_results},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:  # noqa: BLE001  联网失败不影响主流程
        logger.warning("联网搜索失败", exc_info=True)
        return []

    return [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
            "source": "tavily",
        }
        for item in data.get("results", [])
    ]
