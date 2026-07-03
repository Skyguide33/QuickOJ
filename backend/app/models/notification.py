"""Notifications 表 ORM 模型"""
from sqlalchemy import Column, BigInteger, String, DateTime, Boolean, ForeignKey
from app.core.database import Base


class Notification(Base):
    __tablename__ = "Notifications"

    notification_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("Users.user_id"), nullable=True)
    title = Column(String(100), nullable=False)          # NVARCHAR(100)
    content = Column(String(500), nullable=False)        # NVARCHAR(500)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False)
