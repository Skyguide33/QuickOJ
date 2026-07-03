"""排行榜接口路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import PaginationParams
from app.models.user import User
from app.utils.response import paginated, error

router = APIRouter()


@router.get("")
def get_ranking(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(User).filter(User.status == "active") \
            .order_by(User.solved_problems.desc(), User.total_submissions.asc())
        total = query.count()
        users = query.offset(pagination.offset).limit(pagination.size).all()

        rank = pagination.offset + 1
        items = [{
            "rank": rank + i, "user_id": u.user_id, "username": u.username,
            "avatar": u.avatar, "solved_problems": u.solved_problems,
            "total_submissions": u.total_submissions,
        } for i, u in enumerate(users)]

        return paginated(items, pagination.page, pagination.size, total)
    except Exception as e:
        return error(message=str(e))
