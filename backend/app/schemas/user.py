"""用户模块 — Pydantic 请求/响应 Schema"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, field_validator
import re


# ============================================================
# 请求 Schema
# ============================================================

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=4, max_length=20, description="用户名")
    password: str = Field(..., min_length=6, max_length=32, description="密码")
    email: Optional[EmailStr] = Field(None, description="邮箱")

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("用户名只能包含字母、数字和下划线，且首字符不能是数字")
        return v


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="刷新令牌")


class UpdateUserRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=4, max_length=20)
    email: Optional[EmailStr] = None

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError("用户名只能包含字母、数字和下划线，且首字符不能是数字")
        return v


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=32, description="新密码")


# ============================================================
# 响应 Schema
# ============================================================

class UserBrief(BaseModel):
    user_id: int
    username: str
    avatar: Optional[str] = None
    role: str
    solved_problems: int
    total_submissions: int

    class Config:
        from_attributes = True


class UserDetail(BaseModel):
    user_id: int
    username: str
    email: Optional[str] = None
    avatar: Optional[str] = None
    role: str
    status: str
    solved_problems: int
    total_submissions: int
    registered_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    user_id: int
    username: str
    avatar: Optional[str] = None
    role: str
    solved_problems: int
    total_submissions: int
    registered_at: datetime
    recent_accepted: list = []

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    token: str
    expires_in: int
    user: UserBrief


class LoginResponse(BaseModel):
    code: int = 0
    message: str = "登录成功"
    data: TokenResponse
