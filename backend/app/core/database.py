"""
SQLAlchemy 数据库引擎和会话工厂
"""
import warnings
from sqlalchemy import create_engine, exc as sa_exc
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import SQLALCHEMY_DATABASE_URL

warnings.filterwarnings("ignore", category=sa_exc.SAWarning, message=".*server version.*")

# 创建引擎 (SQL Server 连接池配置)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    echo=False,                  # 生产环境设为 False
    connect_args={
        "timeout": 10,           # 连接超时秒数
    }
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 基类
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：获取数据库会话，请求结束后自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
