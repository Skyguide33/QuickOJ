"""标签接口路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.tag import Tag
from app.utils.response import success, error

router = APIRouter()


@router.get("")
def get_tags(
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    db: Session = Depends(get_db),
):
    """获取所有标签列表及每个标签下的题目数量"""
    try:
        query = db.query(Tag)
        if keyword:
            query = query.filter(Tag.tag_name.contains(keyword))
        tags = query.order_by(Tag.problems.desc()).all()

        return success(data=[
            {
                "tag_id": t.tag_id,
                "tag_name": t.tag_name,
                "problem_count": t.problems,
                "description": t.description,
            }
            for t in tags
        ])
    except Exception as e:
        return error(message=str(e))
