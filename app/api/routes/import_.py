"""内容导入接口。"""
from __future__ import annotations

import os
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.import_service import get_task, import_document

router = APIRouter(tags=["import"])

_UPLOAD_DIR = "storage/uploads"


@router.post("/import")
async def upload_document(file: UploadFile = File(...)) -> dict:
    """上传文档并触发导入。"""
    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    filename = os.path.basename(file.filename or "upload.md")
    saved_path = os.path.join(_UPLOAD_DIR, filename)
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    task_id = import_document(saved_path, source_file=file.filename)
    return {"task_id": task_id}


@router.get("/import/tasks/{task_id}")
def get_import_task(task_id: int) -> dict:
    """查询导入任务状态。"""
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task
