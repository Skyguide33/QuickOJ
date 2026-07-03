"""用户模块业务逻辑"""
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.submission import UserAcceptedProblem
from app.models.problem import Problem
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.exceptions import conflict, not_found, unauthorized, forbidden, bad_request
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES


def register_user(db: Session, username: str, password: str, email: Optional[str] = None) -> User:
    """注册新用户。第一个注册的用户自动成为 root"""
    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise conflict("用户名已存在")

    # 检查邮箱是否已存在
    if email:
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise conflict("邮箱已被注册")

    # 检查是否为第一个用户 → 自动设为 root
    is_first = db.query(func.count(User.user_id)).scalar() == 0

    user = User(
        username=username,
        password_hash=hash_password(password),
        email=email,
        role="root" if is_first else "user",
        status="active",
        token_version=0,
        registered_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, username: str, password: str) -> Tuple[str, str, User]:
    """用户登录，返回 (access_token, refresh_token, user)"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise unauthorized("用户名或密码错误")

    if user.status == "banned":
        raise unauthorized("账号已被封禁，请联系管理员")

    if not verify_password(password, user.password_hash):
        raise unauthorized("用户名或密码错误")

    # 更新 token_version（单设备登录）和最后登录时间
    user.token_version += 1
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        user_id=user.user_id,
        role=user.role,
        token_version=user.token_version,
    )
    refresh_token = create_refresh_token(
        user_id=user.user_id,
        token_version=user.token_version,
    )
    return access_token, refresh_token, user


def get_user_detail(db: Session, user_id: int) -> User:
    """获取用户完整信息"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise not_found("用户")
    return user


def get_user_public(db: Session, user_id: int) -> dict:
    """获取用户公开信息（含最近通过的题目）"""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise not_found("用户")

    # 最近通过的 10 道题
    from app.models.views import VUserSolved
    recent = (
        db.query(VUserSolved)
        .filter(VUserSolved.user_id == user_id)
        .order_by(VUserSolved.first_accepted_at.desc())
        .limit(5).all()
    )

    return {
        "user_id": user.user_id,
        "username": user.username,
        "avatar": user.avatar,
        "role": user.role,
        "solved_problems": user.solved_problems,
        "total_submissions": user.total_submissions,
        "registered_at": user.registered_at,
        "recent_accepted": [
            {
                "problem_id": r.problem_id,
                "problem_number": r.problem_number,
                "problem_name": r.problem_name,
                "first_accepted_at": r.first_accepted_at,
            }
            for r in recent
        ]
    }


def get_user_solved_problems(
    db: Session, user_id: int, page: int, size: int
) -> Tuple[list, int]:
    """分页获取用户通过的题目列表"""
    # 先确认用户存在
    if not db.query(User).filter(User.user_id == user_id).first():
        raise not_found("用户")

    from app.models.views import VUserSolved
    query = (
        db.query(VUserSolved)
        .filter(VUserSolved.user_id == user_id)
        .order_by(VUserSolved.first_accepted_at.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()

    return [
        {
            "problem_id": r.problem_id,
            "problem_number": r.problem_number,
            "problem_name": r.problem_name,
            "difficulty": r.difficulty,
            "first_accepted_at": r.first_accepted_at,
        }
        for r in items
    ], total


def update_user_info(
    db: Session, current_user: User, username: Optional[str], email: Optional[str]
) -> User:
    """更新用户名/邮箱"""
    if not username and not email:
        raise bad_request("至少提供一个字段")

    if username and username != current_user.username:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise conflict("用户名已存在")
        current_user.username = username

    if email and email != current_user.email:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise conflict("邮箱已被注册")
        current_user.email = email

    db.commit()
    db.refresh(current_user)
    return current_user


def change_password(
    db: Session, user: User, old_password: str, new_password: str
) -> str:
    """修改密码，返回新的 access_token"""
    if not verify_password(old_password, user.password_hash):
        raise unauthorized("原密码错误")

    user.password_hash = hash_password(new_password)
    user.token_version += 1  # 使所有旧 Token 失效
    db.commit()
    db.refresh(user)

    # 返回新 Token，当前设备保持登录
    return create_access_token(
        user_id=user.user_id,
        role=user.role,
        token_version=user.token_version,
    )


def update_avatar(db: Session, user: User, avatar_path: str) -> User:
    """更新用户头像路径"""
    user.avatar = avatar_path
    db.commit()
    db.refresh(user)
    return user
