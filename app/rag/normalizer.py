"""元数据规范化：来源变体字段映射为规范 schema（对应 BR-002 / TDD §5.2）。"""
from __future__ import annotations

from dataclasses import asdict, dataclass

# 来源字段变体 → 规范字段
_REGION_KEYS = ("城市", "目的地")
_NAME_KEYS = ("景点名称", "线路名称", "住宿名称", "文档名称", "餐厅名称")


@dataclass
class NormalizedMetadata:
    """规范化的元数据。"""

    content_type: str = ""
    region: str = ""
    name: str = ""
    theme: str = ""
    source_file: str = ""
    source_path: str = ""

    def to_dict(self) -> dict[str, str]:
        """转为字典，便于写入数据库与向量库 metadata。"""
        return asdict(self)


def normalize(
    metadata_raw: dict[str, str],
    source_file: str = "",
    source_path: str = "",
) -> NormalizedMetadata:
    """将来源元数据映射为规范 schema，缺失字段填空字符串。"""
    content_type = metadata_raw.get("内容类型", "")
    theme = metadata_raw.get("主题", "")

    region = ""
    for key in _REGION_KEYS:
        if key in metadata_raw:
            region = metadata_raw[key]
            break

    name = ""
    for key in _NAME_KEYS:
        if key in metadata_raw:
            name = metadata_raw[key]
            break

    return NormalizedMetadata(
        content_type=content_type,
        region=region,
        name=name,
        theme=theme,
        source_file=source_file,
        source_path=source_path,
    )
