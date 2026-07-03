"""消息通知接口路由"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, PaginationParams
from app.models.user import User
from app.models.notification import Notification
from app.utils.response import success, error, paginated

router = APIRouter()


# ============================================================
# 5.2 获取消息列表
# ============================================================
@router.get("")
def list_notifications(
    is_read: Optional[int] = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.user_id)

    if is_read is not None:
        query = query.filter(Notification.is_read == bool(is_read))

    total = query.count()
    notifs = query.order_by(Notification.created_at.desc()) \
                  .offset(pagination.offset).limit(pagination.size).all()

    return paginated(
        [
            {
                "notification_id": n.notification_id,
                "title": n.title,
                "content": n.content,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ],
        pagination.page, pagination.size, total,
    )


# ============================================================
# 5.3 获取未读消息数量
# ============================================================
@router.get("/unread-count")
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.user_id,
        Notification.is_read == False,
    ).count()
    return success(data={"unread_count": count})


# ============================================================
# 5.4 标记消息为已读
# ============================================================
@router.put("/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.user_id,
    ).first()

    if not notif:
        return error(message="消息不存在")

    notif.is_read = True
    db.commit()

    return success(message="已标记为已读")


# ============================================================
# 5.5 全部标记为已读
# ============================================================
@router.put("/read-all")
def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.user_id,
            Notification.is_read == False,
        )
        .update({"is_read": True})
    )
    db.commit()

    return success(data={"updated_count": updated}, message="已全部标记为已读")


# ============================================================
# 5.6 删除消息
# ============================================================
@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = db.query(Notification).filter(
        Notification.notification_id == notification_id,
        Notification.user_id == current_user.user_id,
    ).first()

    if not notif:
        return error(message="消息不存在")

    db.delete(notif)
    db.commit()

    return success(message="删除成功")
