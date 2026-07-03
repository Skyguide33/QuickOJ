"""提交记录模块业务逻辑"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session, defer
from sqlalchemy import and_, func

from app.models.submission import Submission
from app.models.problem import Problem
from app.models.user import User
from app.core.exceptions import not_found, forbidden
from app.dependencies import ROLE_LEVEL


def get_submission_status(
    db: Session, submission_id: int, current_user: User
) -> dict:
    """获取提交状态（轻量轮询，不含 code 等不变字段）"""
    submission = db.query(Submission).filter(
        Submission.submission_id == submission_id
    ).first()
    if not submission:
        raise not_found("提交记录")

    is_owner = submission.user_id == current_user.user_id
    is_admin = ROLE_LEVEL[current_user.role] <= ROLE_LEVEL["admin"]
    problem = db.query(Problem).filter(Problem.problem_id == submission.problem_id).first()
    is_uploader = problem and problem.uploader_id == current_user.user_id
    if not (is_owner or is_admin or is_uploader):
        from app.models.submission import UserAcceptedProblem
        solved = db.query(UserAcceptedProblem).filter(
            UserAcceptedProblem.user_id == current_user.user_id,
            UserAcceptedProblem.problem_id == submission.problem_id,
        ).first()
        if not solved:
            raise forbidden("无权查看该提交记录")

    import json
    judged = None
    if submission.judged_result:
        try:
            raw = json.loads(submission.judged_result)
            if isinstance(raw, dict):
                judged = raw.get("tests", [])
        except (json.JSONDecodeError, TypeError):
            judged = submission.judged_result
    # 去掉程序输出和错误消息，太重且无用
    if isinstance(judged, list):
        judged = [{k: v for k, v in t.items() if k not in ("program_output", "message")} for t in judged]

    return {
        "submission_id": submission.submission_id,
        "status": submission.status,
        "run_time": submission.run_time,
        "run_memory": submission.run_memory,
        "judged_at": submission.judged_at.isoformat() if submission.judged_at else None,
        "judged_result": judged,
    }


def get_submission_detail(
    db: Session, submission_id: int, current_user: User
) -> dict:
    """获取提交记录详情（含权限校验）"""
    submission = db.query(Submission).filter(
        Submission.submission_id == submission_id
    ).first()
    if not submission:
        raise not_found("提交记录")

    # 权限：自己的记录 / 管理员 / 题目上传者
    is_owner = submission.user_id == current_user.user_id
    is_admin = ROLE_LEVEL[current_user.role] <= ROLE_LEVEL["admin"]

    problem = db.query(Problem).filter(
        Problem.problem_id == submission.problem_id
    ).first()
    is_uploader = problem and problem.uploader_id == current_user.user_id

    if not (is_owner or is_admin or is_uploader):
        # 还需检查：用户是否通过了该题
        from app.models.submission import UserAcceptedProblem
        solved = db.query(UserAcceptedProblem).filter(
            UserAcceptedProblem.user_id == current_user.user_id,
            UserAcceptedProblem.problem_id == submission.problem_id,
        ).first()
        if not solved:
            raise forbidden("无权查看该提交记录")

    import json
    judged = None
    judged_error = None
    judged_compile = None
    if submission.judged_result:
        try:
            raw = json.loads(submission.judged_result)
            # 提取错误信息和编译信息
            if isinstance(raw, dict):
                judged_error = raw.get("error")
                judged_compile = raw.get("compile")
                # 取 tests 数组，去掉冗长的程序输出
                judged = raw.get("tests", [])
                if isinstance(judged, list):
                    judged = [{k: v for k, v in t.items() if k not in ("program_output", "message")} for t in judged]
        except (json.JSONDecodeError, TypeError):
            judged = submission.judged_result

    return {
        "submission_id": submission.submission_id,
        "user_id": submission.user_id,
        "username": submission.username,
        "problem_id": submission.problem_id,
        "problem_number": submission.problem_number,
        "problem_name": submission.problem_name or (problem.problem_name if problem else None),
        "language": submission.language,
        "code": submission.code,
        "status": submission.status,
        "run_time": submission.run_time,
        "run_memory": submission.run_memory,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "judged_at": submission.judged_at.isoformat() if submission.judged_at else None,
        "judged_result": judged,
        "judged_error": judged_error,
        "judged_compile": judged_compile,
    }


def list_submissions(
    db: Session,
    page: int, size: int,
    current_user: User,
    problem_number: Optional[str] = None,
    username: Optional[str] = None,
    language: Optional[str] = None,
    status: Optional[str] = None,
    is_test_run: Optional[int] = None,
    order_by: str = "submitted_at",
    order: str = "desc",
) -> Tuple[list, int]:
    """分页查询提交记录"""
    is_admin = ROLE_LEVEL[current_user.role] <= ROLE_LEVEL["admin"]

    query = db.query(Submission)

    if is_test_run is not None and is_admin:
        query = query.filter(Submission.is_test_run == is_test_run)
    elif not is_admin:
        query = query.filter(Submission.is_test_run == 0)

    if problem_number is not None:
        val = problem_number.strip()
        if (val.startswith("#") or val.startswith("p")) and val[1:].isdigit():
            query = query.filter(Submission.problem_id == int(val[1:]))
        elif val.isdigit():
            query = query.filter(Submission.problem_number == int(val))
        else:
            query = query.filter(Submission.problem_number == -1)
    if username:
        uval = username.strip()
        if (uval.startswith("#") or uval.isdigit()) and uval.lstrip("#").isdigit():
            uid = int(uval.lstrip("#"))
            query = query.filter(Submission.user_id == uid)
        else:
            query = query.filter(Submission.username == uval)
    if language:
        query = query.filter(Submission.language == language)
    if status:
        query = query.filter(Submission.status == status)

    # 排序
    sort_map = {
        "submitted_at": Submission.submitted_at,
        "run_time": Submission.run_time,
        "run_memory": Submission.run_memory,
        "code_length": Submission.code_length,
    }
    # COUNT 仅查主键（避免子查询拉取 code/judged_result 等 NVARCHAR(MAX) 大字段）
    count_subq = query.with_entities(Submission.submission_id).subquery()
    total = db.query(func.count()).select_from(count_subq).scalar() or 0

    # 排序 + 分页（count 之后才加，避免列重复）
    sort_col = sort_map.get(order_by, Submission.submitted_at)
    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())
    # 列表页不取 code 和 judged_result（NVARCHAR(MAX)，减少传输量）
    rows = query.options(defer(Submission.code), defer(Submission.judged_result)).offset((page - 1) * size).limit(size).all()

    items = []
    for sub in rows:
        items.append({
            "submission_id": sub.submission_id,
            "user_id": sub.user_id,
            "username": sub.username,
            "problem_id": sub.problem_id,
            "problem_number": sub.problem_number,
            "problem_name": sub.problem_name,
            "language": sub.language,
            "status": sub.status,
            "run_time": sub.run_time,
            "run_memory": sub.run_memory,
            "code_length": sub.code_length,
            "is_test_run": sub.is_test_run,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        })

    return items, total
