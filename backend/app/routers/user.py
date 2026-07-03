"""用户模块路由 (10 个接口)"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, decode_token, verify_token_type, create_refresh_token
from app.dependencies import get_current_user, get_optional_user, PaginationParams, ROLE_LEVEL
from app.models.user import User
from app.schemas.user import (
    RegisterRequest, LoginRequest, RefreshRequest,
    UpdateUserRequest, ChangePasswordRequest,
)
from app.services import user_service
from app.utils.response import success, error, paginated
from app.utils.file_utils import save_avatar
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()


# ============================================================
# 1.1 注册
# ============================================================
@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = user_service.register_user(db, req.username, req.password, req.email)
        return success(
            data={"user_id": user.user_id, "username": user.username},
            message="注册成功",
        )
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 1.2 登录
# ============================================================
@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    try:
        access_token, refresh_token, user = user_service.login_user(db, req.username, req.password)
        return success(
            data={
                "token": access_token,
                "refresh_token": refresh_token,
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "avatar": user.avatar,
                    "role": user.role,
                    "solved_problems": user.solved_problems,
                    "total_submissions": user.total_submissions,
                }
            },
            message="登录成功",
        )
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 1.3 获取当前用户信息
# ============================================================
@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return success(data={
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "avatar": current_user.avatar,
        "role": current_user.role,
        "status": current_user.status,
        "solved_problems": current_user.solved_problems,
        "total_submissions": current_user.total_submissions,
        "registered_at": current_user.registered_at.isoformat() if current_user.registered_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    })


# ============================================================
# 1.4 刷新令牌
# ============================================================
@router.post("/refresh")
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(req.refresh_token)
    except Exception:
        return error(message="令牌已过期，请重新登录")

    if not verify_token_type(payload, "refresh"):
        return error(message="令牌类型错误")

    user_id = payload.get("user_id")
    token_version = payload.get("token_version")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        return error(message="用户不存在")
    if user.token_version != token_version:
        return error(message="令牌已失效，请重新登录")

    new_token = create_access_token(
        user_id=user.user_id,
        role=user.role,
        token_version=user.token_version,
    )
    return success(
        data={
            "token": new_token,
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        },
        message="刷新成功",
    )


# ============================================================
# 1.5 登出 (无状态方案，前端清除 Token 即可)
# ============================================================
@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return success(message="登出成功")


# ============================================================
# 1.6 更新用户信息
# ============================================================
@router.put("/{user_id}")
def update_user(
    user_id: int,
    req: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.user_id != user_id:
        return error(message="无权修改其他用户的信息")

    try:
        updated = user_service.update_user_info(db, current_user, req.username, req.email)
        return success(
            data={
                "user_id": updated.user_id,
                "username": updated.username,
                "email": updated.email,
                "avatar": updated.avatar,
            },
            message="更新成功",
        )
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 1.7 上传/修改头像
# ============================================================
@router.put("/{user_id}/avatar")
async def upload_avatar(
    user_id: int,
    avatar: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.user_id != user_id:
        return error(message="仅可修改自己的头像")

    try:
        avatar_path = save_avatar(avatar, user_id)
    except ValueError as e:
        return error(message=str(e))

    user_service.update_avatar(db, current_user, avatar_path)
    return success(
        data={"user_id": user_id, "avatar": avatar_path},
        message="头像更新成功",
    )


# ============================================================
# 1.8 修改密码
# ============================================================
@router.put("/{user_id}/password")
def change_password(
    user_id: int,
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.user_id != user_id:
        return error(message="仅可修改自己的密码")

    try:
        new_token = user_service.change_password(
            db, current_user, req.old_password, req.new_password
        )
        return success(
            data={
                "token": new_token,
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
            message="密码修改成功",
        )
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 1.9 获取用户公开信息（支持用户ID或用户名）
# ============================================================
@router.get("/{identifier}")
def get_user_public(identifier: str, db: Session = Depends(get_db)):
    try:
        # 纯数字 → 按 user_id 查；否则按 username 查
        if identifier.isdigit():
            data = user_service.get_user_public(db, user_id=int(identifier))
        else:
            user = db.query(User).filter(User.username == identifier).first()
            if not user:
                return error(message="用户不存在")
            data = user_service.get_user_public(db, user_id=user.user_id)
        # 序列化 datetime
        data["registered_at"] = data["registered_at"].isoformat() if data.get("registered_at") else None
        for item in data.get("recent_accepted", []):
            if item.get("first_accepted_at"):
                item["first_accepted_at"] = item["first_accepted_at"].isoformat()
        return success(data=data)
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 1.10 获取用户通过的题目列表
# ============================================================
@router.get("/{user_id}/solved")
def get_user_solved(
    user_id: int,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    try:
        items, total = user_service.get_user_solved_problems(
            db, user_id, pagination.page, pagination.size
        )
        for item in items:
            if item.get("first_accepted_at"):
                item["first_accepted_at"] = item["first_accepted_at"].isoformat()
        return paginated(items, pagination.page, pagination.size, total)
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 1.11 获取用户发布的题目列表
# ============================================================
@router.get("/{user_id}/problems")
def get_user_problems(
    user_id: int,
    pagination: PaginationParams = Depends(),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    from app.models.problem import Problem
    try:
        query = (
            db.query(Problem)
            .filter(Problem.uploader_id == user_id)
            .order_by(Problem.created_at.desc())
        )
        # 非本人且非管理员 → 仅可见公开和重新审核的题目
        is_self = current_user and current_user.user_id == user_id
        is_admin = current_user and ROLE_LEVEL[current_user.role] <= ROLE_LEVEL["admin"]
        if not is_self and not is_admin:
            query = query.filter(Problem.problem_status.in_(["approved", "pending_modify"]))
        total = query.count()
        probs = query.offset(pagination.offset).limit(pagination.size).all()
        items = [{
            "problem_id": p.problem_id,
            "problem_number": p.problem_number,
            "problem_name": p.problem_name,
            "problem_status": p.problem_status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        } for p in probs]
        return paginated(items, pagination.page, pagination.size, total)
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))
