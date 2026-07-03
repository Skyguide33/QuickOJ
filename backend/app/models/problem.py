"""Problems 表 ORM 模型"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, ForeignKey
from app.core.database import Base


class Problem(Base):
    __tablename__ = "Problems"

    problem_id = Column(BigInteger, primary_key=True, autoincrement=True)
    problem_number = Column(BigInteger, unique=True, nullable=True)
    uploader_id = Column(BigInteger, ForeignKey("Users.user_id"), nullable=False)
    problem_status = Column(String(20), nullable=False, default="draft")
    problem_name = Column(String(50), nullable=False)  # NVARCHAR(50)
    difficulty = Column(Integer, nullable=False)
    statement = Column(String, nullable=False)          # NVARCHAR(MAX)
    problem_type = Column(String(20), nullable=False)
    time_limit = Column(Integer, nullable=False)       # ms
    memory_limit = Column(Integer, nullable=False)     # KB
    accepted_user_count = Column(Integer, nullable=False, default=0)
    submissions_before_accepted = Column(Integer, nullable=False, default=0)
    source = Column(String(100), nullable=True)
    sample_download_policy = Column(String(20), nullable=False, default="none")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    reviewer_id = Column(BigInteger, ForeignKey("Users.user_id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comment = Column(String(500), nullable=True)
