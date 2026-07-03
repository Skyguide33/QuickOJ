"""Users 表 ORM 模型"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime
from app.core.database import Base


class User(Base):
    __tablename__ = "Users"

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(30), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    status = Column(String(20), nullable=False, default="active")
    email = Column(String(100), nullable=True)
    avatar = Column(String(255), nullable=True)
    solved_problems = Column(Integer, nullable=False, default=0)
    total_submissions = Column(Integer, nullable=False, default=0)
    token_version = Column(Integer, nullable=False, default=0)
    registered_at = Column(DateTime, nullable=False)
    last_login = Column(DateTime, nullable=True)
