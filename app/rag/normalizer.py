"""元数据规范化：来源变体字段映射为规范 schema（对应 BR-002 / TDD §5.2）。"""
from __future__ import annotations

from dataclasses import asdict, dataclass

# 来源字段变体 → 规范字段
_REGION_KEYS = ("城市", "目的地")
_NAME_KEYS = ("景点名称", "线路名称", "住宿名称", "文档名称", "餐厅名称")

# 内容类型取值（BR-001）；PRD 写作「美食推荐」，样例文档写作「美食介绍」，统一为后者
CONTENT_TYPES = ("景点介绍", "线路推荐", "酒店信息", "美食介绍", "交通指南", "文化民俗")
_CONTENT_TYPE_ALIASES = {"美食推荐": "美食介绍"}

# 与 documents 表的列宽一致，防止 LLM 输出过长导致写库失败
_FILLABLE_FIELDS = {"region": 64, "name": 128, "theme": 255}


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
    content_type = _CONTENT_TYPE_ALIASES.get(content_type, content_type)
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


def needs_llm_fallback(meta: NormalizedMetadata) -> bool:
    """内容类型无效，或地区、名称缺失时需要 LLM 兜底（TDD §7.3）。"""
    return meta.content_type not in CONTENT_TYPES or not meta.region or not meta.name


def fill_missing(meta: NormalizedMetadata, extracted: dict) -> None:
    """用 LLM 抽取结果补全缺失字段；文档已声明的有效值不被覆盖，非法输出被丢弃。"""
    if meta.content_type not in CONTENT_TYPES:
        candidate = extracted.get("content_type")
        if isinstance(candidate, str):
            candidate = _CONTENT_TYPE_ALIASES.get(candidate, candidate)
            if candidate in CONTENT_TYPES:
                meta.content_type = candidate

    for field, max_length in _FILLABLE_FIELDS.items():
        value = extracted.get(field)
        if not getattr(meta, field) and isinstance(value, str):
            setattr(meta, field, value.strip()[:max_length])
