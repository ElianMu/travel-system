"""向量库封装：本地 numpy 向量索引（余弦相似度暴力检索）。

数据量级（数百 chunk）下暴力检索即可满足，规避原生向量库在 Windows 下的稳定性问题。
"""
from __future__ import annotations

import os
import threading
from typing import Any

import numpy as np

_INDEX_FILE = os.path.join("storage", "vector_index.npz")

_vector_store: "VectorStore | None" = None


class VectorStore:
    """numpy 向量索引（线程安全）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ids: list[str] = []
        self._documents: list[str] = []
        self._metadatas: list[dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None
        self._load()

    # ---- 持久化 ----
    def _load(self) -> None:
        if not os.path.exists(_INDEX_FILE):
            return
        data = np.load(_INDEX_FILE, allow_pickle=True)
        self._ids = list(data["ids"])
        self._documents = list(data["documents"])
        self._metadatas = list(data["metadatas"])
        self._embeddings = data["embeddings"]

    def _save(self) -> None:
        os.makedirs(os.path.dirname(_INDEX_FILE), exist_ok=True)
        np.savez(
            _INDEX_FILE,
            ids=np.array(self._ids, dtype=object),
            documents=np.array(self._documents, dtype=object),
            metadatas=np.array(self._metadatas, dtype=object),
            embeddings=self._embeddings if self._embeddings is not None else np.zeros((0, 0)),
        )

    # ---- 对外接口 ----
    def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """写入向量片段（含 metadata）。"""
        with self._lock:
            emb = np.array(embeddings, dtype=np.float32)
            self._embeddings = (
                emb if self._embeddings is None else np.vstack([self._embeddings, emb])
            )
            self._ids.extend(ids)
            self._documents.extend(documents)
            self._metadatas.extend(metadatas)
            self._save()

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """余弦相似度检索，支持元数据过滤。"""
        if self._embeddings is None or len(self._ids) == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        q = np.array(query_embedding, dtype=np.float32)
        sims = self._embeddings @ q  # 向量已归一化，点积即余弦相似度

        mask = np.ones(len(self._ids), dtype=bool)
        if where:
            for cond in self._flatten_where(where):
                mask &= self._match_where(cond)

        valid = np.where(mask)[0]
        if len(valid) == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        order = np.argsort(-sims[valid])[:top_k]
        idx = valid[order]

        return {
            "ids": [[self._ids[i] for i in idx]],
            "documents": [[self._documents[i] for i in idx]],
            "metadatas": [[self._metadatas[i] for i in idx]],
            "distances": [[float(1 - sims[i]) for i in idx]],
        }

    def delete_by_document(self, document_id: int) -> None:
        """按文档删除向量片段。"""
        with self._lock:
            keep = [
                i for i, m in enumerate(self._metadatas)
                if m.get("document_id") != document_id
            ]
            if len(keep) == len(self._ids):
                return
            self._ids = [self._ids[i] for i in keep]
            self._documents = [self._documents[i] for i in keep]
            self._metadatas = [self._metadatas[i] for i in keep]
            self._embeddings = (
                self._embeddings[keep] if self._embeddings is not None else None
            )
            self._save()

    def count(self) -> int:
        """片段总数。"""
        return len(self._ids)

    # ---- where 语法 ----
    @staticmethod
    def _flatten_where(where: dict[str, Any]) -> list[dict[str, Any]]:
        if "$and" in where:
            return where["$and"]
        return [where]

    def _match_where(self, cond: dict[str, Any]) -> np.ndarray:
        mask = np.ones(len(self._ids), dtype=bool)
        for k, v in cond.items():
            mask &= np.array([m.get(k) == v for m in self._metadatas])
        return mask


def get_vector_store() -> VectorStore:
    """获取向量库单例（延迟初始化）。"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
