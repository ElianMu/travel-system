"""应用配置：基于 pydantic-settings，支持 .env 与环境变量分层加载。

字段命名与 .env 中的键一一对应（pydantic-settings 默认大小写不敏感）。
"""
import os
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。"""

    # 优先级：环境变量 > .env.{APP_ENV} > .env > 代码默认值
    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{os.getenv('APP_ENV', 'dev')}"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_name: str = "景文智核 · 智能旅游知识库"
    app_version: str = "0.1.0"
    app_env: Literal["dev", "prod"] = "dev"
    log_level: str = "INFO"
    otel_console_export: bool = False

    # 大模型（OpenAI 兼容协议）
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 60.0

    # 联网搜索
    tavily_api_key: str = ""

    # 内部知识库（本地向量检索）
    embedding_model: str = "BAAI/bge-base-zh-v1.5"
    embedding_model_path: str = ""
    knowledge_base_dir: str = "./knowledge_base"
    vector_store_dir: str = "./storage"  # 目录，或以 .npz 结尾的索引文件路径

    # 数据库（MySQL）
    mysql_host: str = "localhost"
    mysql_port: int = 3300
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "travel_kb"
    mysql_charset: str = "utf8mb4"

    # 检索
    retrieve_top_k: int = 5
    # 低于该相似度视为本地召回不足。样例数据实测：相关问题 ≥0.62，无关问题 ≤0.49
    retrieve_min_score: float = 0.55

    @model_validator(mode="after")
    def _require_secrets_in_prod(self) -> "Settings":
        """生产环境缺少密钥时启动即失败，而不是等到第一次问答才报错。"""
        if self.app_env == "prod" and not self.deepseek_api_key:
            raise ValueError("生产环境必须通过环境变量提供 DEEPSEEK_API_KEY")
        return self

    @property
    def vector_index_file(self) -> str:
        """numpy 向量索引文件路径。"""
        location = self.vector_store_dir or "./storage"
        if location.endswith(".npz"):
            return location
        return os.path.join(location, "vector_index.npz")

    @property
    def database_url(self) -> str:
        """SQLAlchemy 连接串。"""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}"
        )


@lru_cache
def get_settings() -> Settings:
    """缓存配置实例，避免重复加载。"""
    return Settings()


settings = get_settings()
