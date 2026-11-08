"""安全校验：路径越界防护（白名单）。"""
from __future__ import annotations

import os

# 允许访问的文件目录白名单
_ALLOWED_DIRS = ("data", "storage/uploads", "knowledge_base")

UPLOAD_DIR = "storage/uploads"
ALLOWED_UPLOAD_SUFFIXES = (".md", ".markdown")


def is_allowed_path(path: str) -> bool:
    """校验文件路径是否位于白名单目录内，防止路径越界访问。"""
    abs_path = os.path.abspath(path)
    for d in _ALLOWED_DIRS:
        abs_dir = os.path.abspath(d)
        if abs_path == abs_dir or abs_path.startswith(abs_dir + os.sep):
            return True
    return False


def is_safe_filename(filename: str) -> bool:
    """文件名必须是单纯的文件名，不得携带任何路径成分。"""
    if not filename or "\0" in filename or filename in (".", ".."):
        return False
    return "/" not in filename and "\\" not in filename
