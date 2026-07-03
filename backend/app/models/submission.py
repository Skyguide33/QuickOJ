"""Submissions 表 + UserAcceptedProblems 表 ORM 模型"""
from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Boolean, ForeignKey
from app.core.database import Base


class Submission(Base):
    __tablename__ = "Submissions"

    submission_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String(50), nullable=True)
    problem_id = Column(BigInteger, nullable=False)
    problem_number = Column(BigInteger, nullable=True)
    problem_name = Column(String(50), nullable=True)
    problem_type = Column(String(20), nullable=False)
    is_test_run = Column(Boolean, nullable=False, default=False)
    code = Column(String, nullable=False)
    code_length = Column(Integer, nullable=False)
    language = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    run_time = Column(Integer, nullable=True)
    run_memory = Column(Integer, nullable=True)
    judged_result = Column(String, nullable=True)
    submitted_at = Column(DateTime, nullable=False)
    judged_at = Column(DateTime, nullable=True)


class UserAcceptedProblem(Base):
    __tablename__ = "UserAcceptedProblems"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("Users.user_id"), nullable=False)
    problem_id = Column(BigInteger, ForeignKey("Problems.problem_id"), nullable=False)
    first_accepted_at = Column(DateTime, nullable=False)
