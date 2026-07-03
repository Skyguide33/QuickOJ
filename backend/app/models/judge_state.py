"""评测机状态表 —— 跨机器通信"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.core.database import Base


class JudgeState(Base):
    __tablename__ = "JudgeState"

    id = Column(Integer, primary_key=True, default=1)
    is_connected = Column(Boolean, nullable=False, default=False)
    last_heartbeat = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="stopped")  # stopped/idle/running/waiting