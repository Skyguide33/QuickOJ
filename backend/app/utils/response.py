"""
统一响应格式封装
"""
from typing import Any, Optional


def success(data: Any = None, message: str = "操作成功") -> dict:
    return {"code": 0, "message": message, "data": data}


def error(message: str = "操作失败", data: Any = None) -> dict:
    return {"code": 1, "message": message, "data": data}


def paginated(list_data: list, page: int, size: int, total: int) -> dict:
    return {
        "code": 0,
        "message": "操作成功",
        "data": {
            "list": list_data,
            "pagination": {
                "page": page,
                "size": size,
                "total": total,
                "total_pages": (total + size - 1) // size if size > 0 else 0,
            }
        }
    }
