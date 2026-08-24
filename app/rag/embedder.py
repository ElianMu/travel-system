"""向量化：本地加载 bge-base-zh-v1.5 生成 768 维向量（对应 TDD §5.4）。"""
from __future__ import annotations

import time

from app.config import settings

_model = None


def _get_model():
    """延迟加载本地 Embedding 模型（缓存，仅加载一次）。"""
    global _model
    if _model is None:
        import torch

        torch.set_num_threads(1)  # 避免 OpenMP 多线程在后台线程中死锁/段错误

        from sentence_transformers import SentenceTransformer

        # 优先使用本地模型路径，避免联网下载
        model_source = settings.embedding_model_path or settings.embedding_model
        _model = SentenceTransformer(model_source)
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """批量生成向量，失败重试（最多 3 次，指数退避）。"""
    model = _get_model()
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            embeddings = model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [embedding.tolist() for embedding in embeddings]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"向量化失败（已重试 3 次）: {last_err}")
