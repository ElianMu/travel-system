"""导入服务：编排文档导入流程，维护任务状态与失败隔离（对应 TDD §5.8）。"""
from __future__ import annotations

import os
from datetime import datetime

from app.models import Chunk, Document, ImportTask, SessionLocal
from app.rag.embedder import embed
from app.rag.loader import load_markdown
from app.rag.normalizer import normalize
from app.rag.splitter import split_body
from app.rag.store import get_vector_store


def import_document(file_path: str, source_file: str | None = None) -> int:
    """创建导入任务并同步执行，返回任务 ID。

    同步执行（而非后台线程）：torch 与 pymysql 在后台线程中存在原生库冲突（段错误），
    主线程同步执行可稳定规避。任务状态仍记录于 import_tasks 表，可查询。
    """
    name = source_file or os.path.basename(file_path)
    db = SessionLocal()
    task = ImportTask(file_name=name, status="created")
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id
    db.close()

    _run_import(task_id, file_path, name)
    return task_id


def _run_import(task_id: int, file_path: str, source_file: str) -> None:
    """后台执行导入，异常仅标记本任务失败（失败隔离）。"""
    db = SessionLocal()
    try:
        task = db.get(ImportTask, task_id)
        if task is None:
            return
        task.status = "running"
        db.commit()

        # 1. 加载 + 2. 规范化
        doc = load_markdown(file_path)
        meta = normalize(doc.metadata_raw, source_file=source_file, source_path=file_path)

        # 3. 写入文档元数据
        document = Document(
            source_file=meta.source_file,
            source_path=meta.source_path,
            content_type=meta.content_type,
            region=meta.region,
            name=meta.name,
            theme=meta.theme,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        # 4. 切分
        chunks = split_body(doc.body)
        task.total_chunks = len(chunks)
        db.commit()

        # 5. 批量向量化 + 写入向量库与 chunks 表
        if chunks:
            contents = [c.content for c in chunks]
            vectors = embed(contents)
            store = get_vector_store()
            store.add(
                ids=[f"doc-{document.id}-chunk-{i}" for i in range(len(chunks))],
                documents=contents,
                embeddings=vectors,
                metadatas=[
                    {
                        "document_id": document.id,
                        "content_type": meta.content_type,
                        "region": meta.region,
                        "name": meta.name,
                        "heading_path": c.heading_path,
                        "source_file": meta.source_file,
                    }
                    for c in chunks
                ],
            )
            for i, c in enumerate(chunks):
                db.add(
                    Chunk(
                        document_id=document.id,
                        chunk_index=i,
                        heading_path=c.heading_path,
                        content=c.content,
                        vector_id=f"doc-{document.id}-chunk-{i}",
                    )
                )
            task.processed_chunks = len(chunks)

        # 6. 成功
        task.status = "success"
        task.finished_at = datetime.now()
        db.commit()
    except Exception as exc:  # noqa: BLE001  失败隔离：仅本任务失败，不影响其他任务与服务
        db.rollback()
        task = db.get(ImportTask, task_id)
        if task is not None:
            task.status = "failed"
            task.error_message = str(exc)
            task.finished_at = datetime.now()
            db.commit()
    finally:
        db.close()


def get_task(task_id: int) -> dict | None:
    """查询任务状态。"""
    db = SessionLocal()
    task = db.get(ImportTask, task_id)
    if task is None:
        db.close()
        return None
    result = {
        "id": task.id,
        "file_name": task.file_name,
        "status": task.status,
        "total_chunks": task.total_chunks,
        "processed_chunks": task.processed_chunks,
        "error_message": task.error_message,
    }
    db.close()
    return result
