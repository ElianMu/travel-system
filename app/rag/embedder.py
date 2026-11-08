"""向量化：本地加载 bge-base-zh-v1.5 生成 768 维向量（对应 TDD §5.4）。"""
from __future__ import annotations

from app.config import settings
from app.core.resilience import call_with_resilience, embedding_breaker

_model = None
_BATCH_SIZE = 32


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
    """批量生成向量，失败重试（最多 3 次，指数退避）并熔断。

    模型在本进程内运行，同步推理无法被安全中断，因此不设调用超时。
    """
    model = _get_model()

    def encode() -> list[list[float]]:
        embeddings = model.encode(
            texts,
            batch_size=_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [embedding.tolist() for embedding in embeddings]

    return call_with_resilience(embedding_breaker, encode)
