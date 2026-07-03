"""Tags 表 + TagProblems 表 ORM 模型"""
from sqlalchemy import Column, BigInteger, String, Integer, ForeignKey
from app.core.database import Base


class Tag(Base):
    __tablename__ = "Tags"

    tag_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tag_name = Column(String(50), unique=True, nullable=False)   # SQL Server 实际存储为 NVARCHAR
    description = Column(String(500), nullable=True)
    problems = Column(BigInteger, nullable=False, default=0)


class TagProblem(Base):
    __tablename__ = "TagProblems"

    tag_id = Column(BigInteger, ForeignKey("Tags.tag_id"), primary_key=True)
    problem_id = Column(BigInteger, ForeignKey("Problems.problem_id"), primary_key=True)
