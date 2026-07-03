"""
FastAPI 依赖注入：认证、授权、分页参数
"""
from typing import Optional
from fastapi import Depends, Query, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token, verify_token_type
from app.models.user import User
from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

# 角色等级 (数值越小权限越高)
ROLE_LEVEL = {"root": 1, "admin": 2, "user": 3}

# HTTP Bearer 安全方案（Swagger Authorize 按钮直接输入 token）
bearer_scheme = HTTPBearer(bearerFormat="JWT", auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    从请求头 Authorization 中解析 JWT，返回当前登录用户。
    未登录返回 401。
    """
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="未登录，请在 Authorization Header 中提供 Bearer Token")

    token = credentials.credentials

    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="令牌无效或已过期")

    if not verify_token_type(payload, "access"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="令牌类型错误，需要 Access Token")

    user_id = payload.get("user_id")
    token_version = payload.get("token_version")

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="令牌内容无效")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="用户不存在")

    if user.status == "banned":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="账号已被封禁")

    if user.token_version != token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail="账号已在其他设备登录，请重新登录")

    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """可选认证：登录则返回用户，未登录返回 None"""
    if not credentials:
        return None
    try:
        token = credentials.credentials
        payload = decode_token(token)
        if not verify_token_type(payload, "access"):
            return None
        user_id = payload.get("user_id")
        user = db.query(User).filter(User.user_id == user_id).first()
        if user and user.status == "active":
            return user
    except Exception:
        pass
    return None


def require_role(min_role: str):
    """依赖工厂：要求当前用户角色 >= min_role"""
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if ROLE_LEVEL[current_user.role] > ROLE_LEVEL[min_role]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                              detail="无权限访问")
        return current_user
    return checker


class PaginationParams:
    """分页查询参数依赖"""
    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码"),
        size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="每页条数"),
    ):
        self.page = page
        self.size = size
        self.offset = (page - 1) * size
