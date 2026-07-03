"""提交记录接口路由"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, PaginationParams
from app.models.user import User
from app.services import submission_service
from app.utils.response import success, error, paginated

router = APIRouter()


# ============================================================
# 3.7 获取提交记录列表（全局）
# ============================================================
@router.get("")
def list_submissions(
    problem_number: Optional[str] = Query(None, description="题号或 #{id}"),
    username: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_test_run: Optional[int] = Query(None, description="筛选审核提交: 0=正式 1=审核"),
    order_by: str = Query("submitted_at"),
    order: str = Query("desc"),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        items, total = submission_service.list_submissions(
            db,
            page=pagination.page,
            size=pagination.size,
            current_user=current_user,
            problem_number=problem_number,
            username=username,
            language=language,
            status=status,
            is_test_run=is_test_run,
            order_by=order_by,
            order=order,
        )
        return paginated(items, pagination.page, pagination.size, total)
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 3.6 获取提交记录详情
# ============================================================
@router.get("/{submission_id}")
def get_submission_detail(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = submission_service.get_submission_detail(db, submission_id, current_user)
        return success(data=data)
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 3.6b 获取提交状态（轻量轮询，不含 code 等静态字段）
# ============================================================
@router.get("/{submission_id}/status")
def get_submission_status(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        data = submission_service.get_submission_status(db, submission_id, current_user)
        return success(data=data)
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))
