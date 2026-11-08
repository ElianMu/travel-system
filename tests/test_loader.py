"""文档解析与元数据规范化：用 data/ 下真实文档验收（S2）。"""
from pathlib import Path

import pytest

from app.rag.loader import load_markdown, parse_markdown
from app.rag.normalizer import CONTENT_TYPES, normalize

DATA_FILES = sorted(Path("data").rglob("*.md"))


def test_all_sample_documents_present():
    assert len(DATA_FILES) == 30


@pytest.mark.parametrize("path", DATA_FILES, ids=lambda p: p.name)
def test_real_document_parsing(path):
    doc = load_markdown(str(path))
    meta = normalize(doc.metadata_raw, source_file=path.name, source_path=str(path))

    assert doc.title
    assert meta.content_type in CONTENT_TYPES
    assert meta.region
    assert meta.theme
    assert meta.source_file == path.name
    # 交通指南的来源文档没有名称字段，其余类型必须映射出 name
    if meta.content_type != "交通指南":
        assert meta.name
    # 元数据区块不进入正文，H2 层级保留
    assert "## 元数据" not in doc.body
    assert doc.body.startswith("## ")


def test_parse_halfwidth_colon():
    doc = parse_markdown("# 标题\n## 元数据\n- 城市: 三亚\n\n## 正文\n内容")
    assert doc.metadata_raw == {"城市": "三亚"}


def test_food_type_alias_is_canonicalized():
    assert normalize({"内容类型": "美食推荐"}).content_type == "美食介绍"
