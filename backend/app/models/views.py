"""数据库视图对应的只读 ORM 映射"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime
from app.core.database import Base


class VReviewQueue(Base):
    """待审核题目队列"""
    __tablename__ = "v_review_queue"
    problem_id = Column(BigInteger, primary_key=True)
    problem_number = Column(BigInteger)
    problem_name = Column(String(50))
    problem_status = Column(String(20))
    difficulty = Column(Integer)
    problem_type = Column(String(20))
    uploader_id = Column(BigInteger)
    updated_at = Column(DateTime)
    created_at = Column(DateTime)


class VUserSolved(Base):
    """用户已通过题目"""
    __tablename__ = "v_user_solved"
    user_id = Column(BigInteger, primary_key=True)
    problem_id = Column(BigInteger, primary_key=True)
    first_accepted_at = Column(DateTime)
    problem_number = Column(BigInteger)
    problem_name = Column(String(50))
    difficulty = Column(Integer)
