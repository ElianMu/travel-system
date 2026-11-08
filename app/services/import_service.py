"""导入服务：编排文档导入流程，维护任务状态与失败隔离（对应 TDD §5.8）。"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from app.models import Chunk, Document, ImportTask, SessionLocal
from app.rag.embedder import embed
from app.rag.loader import load_markdown
from app.rag.normalizer import CONTENT_TYPES, normalize
from app.rag.splitter import split_body
from app.rag.store import get_vector_store

logger = logging.getLogger(__name__)


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
    """执行导入，异常仅标记本任务失败（失败隔离）。

    文档、片段与向量同进退：向量写入后关系库才提交，失败时回滚并清理已写入的向量。
    """
    db = SessionLocal()
    document_id: int | None = None
    try:
        task = db.get(ImportTask, task_id)
        if task is None:
            return
        task.status = "running"
        db.commit()

        # 1. 加载 + 2. 规范化 + 3. 切分
        doc = load_markdown(file_path)
        meta = normalize(doc.metadata_raw, source_file=source_file, source_path=file_path)
        if meta.content_type not in CONTENT_TYPES:
            raise ValueError(f"内容类型无效：{meta.content_type or '缺失'}")
        chunks = split_body(doc.body)
        if not chunks:
            raise ValueError("文档正文为空")
        task.total_chunks = len(chunks)
        db.commit()

        # 4. 向量化（耗时且易失败，放在写库之前）
        vectors = embed([c.content for c in chunks])

        # 5. 写入文档与片段（暂不提交）
        document = Document(
            source_file=meta.source_file,
            source_path=meta.source_path,
            content_type=meta.content_type,
            region=meta.region,
            name=meta.name,
            theme=meta.theme,
        )
        db.add(document)
        db.flush()
        document_id = document.id
        chunk_rows = [
            Chunk(
                document_id=document.id,
                chunk_index=i,
                heading_path=c.heading_path,
                content=c.content,
                vector_id=f"doc-{document.id}-chunk-{i}",
            )
            for i, c in enumerate(chunks)
        ]
        db.add_all(chunk_rows)
        db.flush()

        # 6. 写入向量库
        store = get_vector_store()
        store.add(
            ids=[row.vector_id for row in chunk_rows],
            documents=[row.content for row in chunk_rows],
            embeddings=vectors,
            metadatas=[_vector_metadata(document, row) for row in chunk_rows],
        )

        # 7. 同名文件视为新版本，替换旧数据；成功后提交
        replaced_ids = _delete_previous_versions(db, source_file, keep_id=document.id)
        task.processed_chunks = len(chunks)
        task.status = "success"
        task.finished_at = datetime.now()
        db.commit()

        for old_id in replaced_ids:
            _discard_vectors(old_id)
        logger.info("导入成功 file=%s chunks=%d replaced=%s", source_file, len(chunks), replaced_ids)
    except Exception as exc:  # noqa: BLE001  失败隔离：仅本任务失败，不影响其他任务与服务
        logger.exception("导入失败 file=%s", source_file)
        db.rollback()
        task = db.get(ImportTask, task_id)
        if task is not None:
            task.status = "failed"
            task.error_message = str(exc)
            task.finished_at = datetime.now()
            db.commit()
        if document_id is not None:
            _discard_vectors(document_id)
    finally:
        db.close()


def _vector_metadata(document: Document, chunk: Chunk) -> dict[str, Any]:
    """构造向量条目的 metadata。"""
    return {
        "document_id": document.id,
        "content_type": document.content_type,
        "region": document.region,
        "name": document.name,
        "theme": document.theme,
        "heading_path": chunk.heading_path,
        "source_file": document.source_file,
    }


def _delete_previous_versions(db, source_file: str, keep_id: int) -> list[int]:
    """删除同名文档的旧版本（元数据与片段），返回被删除的文档 ID。"""
    old_ids = [
        row.id
        for row in db.query(Document.id)
        .filter(Document.source_file == source_file, Document.id != keep_id)
        .all()
    ]
    if old_ids:
        db.query(Chunk).filter(Chunk.document_id.in_(old_ids)).delete(synchronize_session=False)
        db.query(Document).filter(Document.id.in_(old_ids)).delete(synchronize_session=False)
    return old_ids


def _discard_vectors(document_id: int) -> None:
    """清理文档的向量；清理失败只记日志，可通过重建索引修复。"""
    try:
        get_vector_store().delete_by_document(document_id)
    except Exception:  # noqa: BLE001
        logger.exception("向量清理失败 document_id=%s，可运行 scripts.rebuild_index 修复", document_id)


def rebuild_vector_index() -> int:
    """由 documents 与 chunks 表全量重建向量索引，返回片段数（NFR-DATA-001）。"""
    db = SessionLocal()
    try:
        rows = (
            db.query(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .order_by(Document.id, Chunk.chunk_index)
            .all()
        )
        ids = [chunk.vector_id for chunk, _ in rows]
        contents = [chunk.content for chunk, _ in rows]
        metadatas = [_vector_metadata(document, chunk) for chunk, document in rows]
    finally:
        db.close()

    get_vector_store().replace_all(ids, contents, embed(contents) if contents else [], metadatas)
    return len(ids)


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
