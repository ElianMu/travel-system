"""splitter 结构化切分单元测试。"""
from app.rag.splitter import split_body


def test_split_by_h2():
    """按 H2 边界切分。"""
    body = "## 一\n内容一\n## 二\n内容二"
    chunks = split_body(body)
    assert len(chunks) == 2
    assert chunks[0].heading_path == "一"
    assert chunks[1].heading_path == "二"


def test_split_h3_subsection():
    """H2 过大时按 H3 细分，且无空标题残留。"""
    big = "## 景点\n" + "".join(f"### 景点{i}\n" + "内容" * 200 + "\n" for i in range(5))
    chunks = split_body(big)
    assert len(chunks) == 5
    assert all(c.heading_path.startswith("景点 > 景点") for c in chunks)
    assert all(len(c.content) > 50 for c in chunks)


def test_heading_path():
    """heading_path 记录 H2 > H3 层级。"""
    content = "介绍" * 700  # 超过 max_chunk_size，触发 H3 细分
    body = "## 核心景点推荐\n### 蜈支洲岛\n" + content
    chunks = split_body(body)
    assert chunks[0].heading_path == "核心景点推荐 > 蜈支洲岛"


def test_intro_before_first_h3_is_kept():
    """首个 H3 之前的导语不能丢失。"""
    body = "## 景点\n这是导语。\n### 甲\n" + "内容" * 400
    chunks = split_body(body)
    assert [c.heading_path for c in chunks] == ["景点", "景点 > 甲"]
    assert "这是导语" in chunks[0].content


def test_large_h2_without_h3_is_kept_whole():
    """过大的 H2 没有 H3 可细分时保留整块。"""
    text = "内容" * 400
    chunks = split_body(f"## 概览\n{text}")
    assert len(chunks) == 1
    assert chunks[0].heading_path == "概览"
    assert text in chunks[0].content


def test_chunk_index_is_sequential():
    body = "## 一\n甲\n## 二\n" + "".join(f"### {i}\n" + "内容" * 200 + "\n" for i in range(3))
    assert [c.chunk_index for c in split_body(body)] == list(range(4))
