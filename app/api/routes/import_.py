"""内容导入接口。"""
from __future__ import annotations

import os
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.security import (
    ALLOWED_UPLOAD_SUFFIXES,
    UPLOAD_DIR,
    is_allowed_path,
    is_safe_filename,
)
from app.services.import_service import get_task, import_document

router = APIRouter(tags=["import"])


@router.post("/import")
async def upload_document(file: UploadFile = File(...)) -> dict:
    """上传文档并触发导入。"""
    filename = file.filename or ""
    if not is_safe_filename(filename):
        raise HTTPException(status_code=403, detail="非法文件路径")
    if not filename.lower().endswith(ALLOWED_UPLOAD_SUFFIXES):
        raise HTTPException(status_code=400, detail="仅支持 Markdown 文档（.md / .markdown）")

    saved_path = os.path.join(UPLOAD_DIR, filename)
    if not is_allowed_path(saved_path):
        raise HTTPException(status_code=403, detail="非法文件路径")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    task_id = import_document(saved_path, source_file=filename)
    return {"task_id": task_id}


@router.get("/import/tasks/{task_id}")
def get_import_task(task_id: int) -> dict:
    """查询导入任务状态。"""
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task
