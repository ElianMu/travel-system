"""向量库封装：本地 numpy 向量索引（余弦相似度暴力检索）。

数据量级（数百 chunk）下暴力检索即可满足，规避原生向量库在 Windows 下的稳定性问题。
"""
from __future__ import annotations

import os
import threading
from typing import Any

import numpy as np

from app.config import settings

_EMPTY_RESULT = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

_vector_store: "VectorStore | None" = None
_singleton_lock = threading.Lock()


class VectorStore:
    """numpy 向量索引（线程安全）。"""

    def __init__(self, index_file: str | None = None) -> None:
        self._index_file = index_file or settings.vector_index_file
        self._lock = threading.Lock()
        self._ids: list[str] = []
        self._documents: list[str] = []
        self._metadatas: list[dict[str, Any]] = []
        self._embeddings: np.ndarray | None = None
        self._load()

    # ---- 持久化 ----
    def _load(self) -> None:
        if not os.path.exists(self._index_file):
            return
        data = np.load(self._index_file, allow_pickle=True)
        self._ids = list(data["ids"])
        self._documents = list(data["documents"])
        self._metadatas = list(data["metadatas"])
        self._embeddings = data["embeddings"]

    def _save(self) -> None:
        """先写临时文件再原子替换，进程中断时不会损坏已有索引。"""
        directory = os.path.dirname(self._index_file)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_file = f"{self._index_file}.tmp.npz"
        np.savez(
            tmp_file,
            ids=np.array(self._ids, dtype=object),
            documents=np.array(self._documents, dtype=object),
            metadatas=np.array(self._metadatas, dtype=object),
            embeddings=self._embeddings if self._embeddings is not None else np.zeros((0, 0)),
        )
        os.replace(tmp_file, self._index_file)

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
                emb if self._embeddings is None or not self._ids
                else np.vstack([self._embeddings, emb])
            )
            self._ids.extend(ids)
            self._documents.extend(documents)
            self._metadatas.extend(metadatas)
            self._save()

    def replace_all(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """整体替换索引内容（用于由关系库重建向量索引）。"""
        with self._lock:
            self._ids = list(ids)
            self._documents = list(documents)
            self._metadatas = list(metadatas)
            self._embeddings = np.array(embeddings, dtype=np.float32) if ids else None
            self._save()

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """余弦相似度检索，支持元数据过滤。"""
        with self._lock:
            if self._embeddings is None or len(self._ids) == 0:
                return _EMPTY_RESULT

            q = np.array(query_embedding, dtype=np.float32)
            sims = self._embeddings @ q  # 向量已归一化，点积即余弦相似度

            mask = np.ones(len(self._ids), dtype=bool)
            if where:
                for cond in self._flatten_where(where):
                    mask &= self._match_where(cond)

            valid = np.where(mask)[0]
            if len(valid) == 0:
                return _EMPTY_RESULT

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

    def get_document_chunks(self, document_id: int) -> list[tuple[str, str]]:
        """按写入顺序返回文档的片段：(heading_path, 文本)。"""
        with self._lock:
            return [
                (m.get("heading_path") or "", text)
                for m, text in zip(self._metadatas, self._documents)
                if m.get("document_id") == document_id
            ]

    def count(self) -> int:
        """片段总数。"""
        with self._lock:
            return len(self._ids)

    # ---- where 语法 ----
    @staticmethod
    def _flatten_where(where: dict[str, Any]) -> list[dict[str, Any]]:
        if "$and" in where:
            return where["$and"]
        return [where]

    def _match_where(self, cond: dict[str, Any]) -> np.ndarray:
        """等值匹配；值为 {"$contains": s} 时做子串匹配（如 region 含多个城市）。"""
        mask = np.ones(len(self._ids), dtype=bool)
        for key, expected in cond.items():
            if isinstance(expected, dict) and "$contains" in expected:
                needle = expected["$contains"]
                mask &= np.array([needle in (m.get(key) or "") for m in self._metadatas])
            else:
                mask &= np.array([m.get(key) == expected for m in self._metadatas])
        return mask


def get_vector_store() -> VectorStore:
    """获取向量库单例（延迟初始化）。"""
    global _vector_store
    with _singleton_lock:
        if _vector_store is None:
            _vector_store = VectorStore()
        return _vector_store
