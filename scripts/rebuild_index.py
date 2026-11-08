"""由 MySQL 中的 documents 与 chunks 表全量重建向量索引。"""
from app.rag.embedder import embed

embed(["预热"])  # 预热 Embedding 模型，规避原生库冲突

from app.services.import_service import rebuild_vector_index  # noqa: E402


def main() -> None:
    print(f"向量索引重建完成：{rebuild_vector_index()} 个片段")


if __name__ == "__main__":
    main()
