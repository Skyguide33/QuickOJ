"""
JWT Token 生成/校验 + 密码哈希
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import (
    JWT_SECRET_KEY, JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES,
)

# 密码哈希上下文 (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对明文密码做 bcrypt 哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希值是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: int,
    role: str,
    token_version: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """生成 JWT Access Token"""
    to_encode = {
        "user_id": user_id,
        "role": role,
        "token_version": token_version,
        "type": "access",
    }
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int, token_version: int) -> str:
    """生成 JWT Refresh Token"""
    to_encode = {
        "user_id": user_id,
        "token_version": token_version,
        "type": "refresh",
    }
    expire = datetime.utcnow() + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    解码 JWT Token，返回 payload。
    若 Token 无效或过期，抛出 JWTError。
    """
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def verify_token_type(payload: dict, expected_type: str) -> bool:
    """校验 Token 类型 (access / refresh)"""
    return payload.get("type") == expected_type
