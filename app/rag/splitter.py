"""结构化切分：按 H2/H3 标题边界切分正文（对应 TDD §5.3）。"""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MAX_CHUNK_SIZE = 600


@dataclass
class Chunk:
    """切分片段。"""

    content: str          # 片段正文（含标题行）
    heading_path: str     # 标题路径（如「核心景点推荐 > 蜈支洲岛」）
    chunk_index: int      # 文档内序号


def split_body(body: str, max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE) -> list[Chunk]:
    """按 H2 边界切分，块过大时按 H3 细分。"""
    chunks: list[Chunk] = []
    idx = 0

    for h2_title, h2_text in _sections(body, level=2):
        if not h2_text.strip():
            continue
        if len(h2_text) <= max_chunk_size:
            chunks.append(Chunk(content=h2_text, heading_path=h2_title, chunk_index=idx))
            idx += 1
        else:
            sub_sections = _sections(h2_text, level=3)
            if sub_sections:
                for h3_title, h3_text in sub_sections:
                    if not h3_title or not h3_text.strip():
                        # 跳过 H2 标题残留（无 H3 子标题的空 section）
                        continue
                    path = f"{h2_title} > {h3_title}"
                    chunks.append(Chunk(content=h3_text, heading_path=path, chunk_index=idx))
                    idx += 1
            else:
                # 无 H3 可细分，保留整块（语义完整优先于长度）
                chunks.append(Chunk(content=h2_text, heading_path=h2_title, chunk_index=idx))
                idx += 1

    return chunks


def _sections(text: str, level: int) -> list[tuple[str, str]]:
    """按指定级别标题分割，返回 [(标题, 含标题行的完整文本)]。"""
    prefix = "#" * level + " "
    lines = text.splitlines()
    sections: list[tuple[str, str]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        if line.startswith(prefix):
            if current_title or current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[len(prefix):].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_title or current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return sections
