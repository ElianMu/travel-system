"""normalizer 元数据规范化单元测试。"""
from app.rag.normalizer import normalize


def test_region_variant_mapping():
    """城市/目的地 → region。"""
    m = normalize({"内容类型": "线路推荐", "目的地": "昆明、大理、丽江", "线路名称": "昆大丽 6 日游", "主题": "古城"})
    assert m.region == "昆明、大理、丽江"
    assert m.name == "昆大丽 6 日游"
    assert m.content_type == "线路推荐"


def test_name_variant_mapping():
    """景点名称/线路名称/住宿名称/文档名称 → name。"""
    assert normalize({"内容类型": "景点介绍", "景点名称": "蜈支洲岛"}).name == "蜈支洲岛"
    assert normalize({"内容类型": "酒店信息", "住宿名称": "三亚住宿推荐"}).name == "三亚住宿推荐"
    assert normalize({"内容类型": "美食介绍", "文档名称": "成都美食推荐"}).name == "成都美食推荐"


def test_missing_fields_default_empty():
    """缺失字段填空字符串（如交通指南无 name）。"""
    m = normalize({"内容类型": "交通指南", "城市": "三亚", "主题": "机场、高铁"})
    assert m.name == ""
    assert m.region == "三亚"


def test_source_fields():
    """来源文件与路径。"""
    m = normalize({}, source_file="a.md", source_path="data/a.md")
    assert m.source_file == "a.md"
    assert m.source_path == "data/a.md"
