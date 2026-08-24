"""向量库封装（ChromaDB 1.5.x）。

通过本模块隔离 Chroma 依赖（Port/Adapter），未来可替换为 Milvus。
"""
from __future__ import annotations

import threading
from typing import Any

from app.config import settings

COLLECTION_NAME = "travel_kb"

_vector_store: "VectorStore | None" = None


class VectorStore:
    """向量库访问封装（写操作线程安全）。"""

    def __init__(self) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        # 独立持久化目录；chromadb 的 Rust 后端无法写含中文路径，需 ASCII 路径
        persist_dir = settings.vector_store_dir or "./storage/chroma"
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._lock = threading.Lock()

    def add(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """写入向量片段（含 metadata）。"""
        with self._lock:
            self._collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """向量检索，支持元数据过滤。"""
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where
        return self._collection.query(**kwargs)

    def delete_by_document(self, document_id: int) -> None:
        """按文档删除向量片段。"""
        with self._lock:
            self._collection.delete(where={"document_id": document_id})

    def count(self) -> int:
        """片段总数。"""
        return self._collection.count()


def get_vector_store() -> VectorStore:
    """获取向量库单例（延迟初始化）。"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
