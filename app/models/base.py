"""数据库基础设施：引擎、会话、建表。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # 空闲连接自动探测，避免 MySQL 超时断连
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """ORM 基类。"""


def init_db() -> None:
    """创建所有表（应用启动时调用）。"""
    from app.models import entities  # noqa: F401  确保模型注册到 Base.metadata

    Base.metadata.create_all(bind=engine)
