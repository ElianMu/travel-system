"""应用配置：基于 pydantic-settings，支持 .env 与环境变量分层加载。

字段命名与 .env 中的键一一对应（pydantic-settings 默认大小写不敏感）。
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_name: str = "景文智核 · 智能旅游知识库"
    app_version: str = "0.1.0"

    # 大模型（OpenAI 兼容协议）
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    # 联网搜索
    tavily_api_key: str = ""

    # 内部知识库（本地向量检索）
    embedding_model: str = "BAAI/bge-base-zh-v1.5"
    embedding_model_path: str = ""
    knowledge_base_dir: str = "./knowledge_base"
    vector_store_dir: str = "./storage/chroma"

    # 数据库（MySQL）
    mysql_host: str = "localhost"
    mysql_port: int = 3300
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "travel_kb"
    mysql_charset: str = "utf8mb4"

    # 检索
    retrieve_top_k: int = 5

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
