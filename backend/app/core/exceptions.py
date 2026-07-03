"""
自定义异常类 + 全局异常处理器
"""
from fastapi import HTTPException, status


class OJException(HTTPException):
    """OJ 业务异常基类"""
    def __init__(self, status_code: int, message: str):
        super().__init__(status_code=status_code, detail=message)


# ---- 常用异常快捷构造 ----

def not_found(entity: str = "资源") -> OJException:
    return OJException(status.HTTP_404_NOT_FOUND, f"{entity}不存在")


def unauthorized(message: str = "未登录或令牌已过期") -> OJException:
    return OJException(status.HTTP_401_UNAUTHORIZED, message)


def forbidden(message: str = "无权限访问") -> OJException:
    return OJException(status.HTTP_403_FORBIDDEN, message)


def bad_request(message: str = "请求参数错误") -> OJException:
    return OJException(status.HTTP_400_BAD_REQUEST, message)


def conflict(message: str = "资源已存在") -> OJException:
    return OJException(status.HTTP_409_CONFLICT, message)
