"""文档加载：解析 Markdown 的标题、元数据区块与正文（对应 TDD §5.1）。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LoadedDocument:
    """解析后的文档结构。"""

    title: str                                  # 一级标题
    metadata_raw: dict[str, str] = field(default_factory=dict)  # 元数据区块键值对
    body: str = ""                              # 正文（保留 H2/H3 标题层级）


def load_markdown(path: str) -> LoadedDocument:
    """读取并解析 Markdown 文件。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return parse_markdown(text)


def parse_markdown(text: str) -> LoadedDocument:
    """解析 Markdown 文本为 LoadedDocument。"""
    lines = text.splitlines()
    title = ""
    metadata: dict[str, str] = {}
    body_start = 0

    # 1. 一级标题
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # 2. 元数据区块：从 "## 元数据" 到下一个 "## " 之间
    meta_start = -1
    for i, line in enumerate(lines):
        if line.strip() == "## 元数据":
            meta_start = i
            break

    if meta_start >= 0:
        for i in range(meta_start + 1, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith("## "):
                body_start = i
                break
            if stripped.startswith("- "):
                kv = stripped[2:]
                key, sep, value = kv.partition("：")
                if not sep:
                    key, sep, value = kv.partition(":")
                if sep and value:
                    metadata[key.strip()] = value.strip()
        else:
            # 元数据区块后无正文（罕见）
            body_start = len(lines)

    # 3. 正文
    body = "\n".join(lines[body_start:]).strip()
    return LoadedDocument(title=title, metadata_raw=metadata, body=body)
