"""题目模块业务逻辑"""
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.problem import Problem
from app.models.tag import Tag, TagProblem
from app.models.user import User
from app.models.submission import Submission, UserAcceptedProblem
from app.core.exceptions import not_found, forbidden, bad_request, conflict
from app.dependencies import ROLE_LEVEL


def can_access_problem(user: Optional[User], problem: Problem) -> bool:
    """判断用户是否可以访问题目详情"""
    if problem.problem_status in ("approved", "pending_modify"):
        return True
    if problem.problem_status in ("pending_new", "rejected"):
        # 上传者或管理员可见
        if user and (user.user_id == problem.uploader_id or ROLE_LEVEL[user.role] <= ROLE_LEVEL["admin"]):
            return True
        return False
    if problem.problem_status in ("frozen", "archived"):
        # 仅管理员可见
        if user and ROLE_LEVEL[user.role] <= ROLE_LEVEL["admin"]:
            return True
        return False
    return False


def get_problem_detail(
    db: Session,
    problem_id: Optional[int] = None,
    problem_number: Optional[int] = None,
    current_user: Optional[User] = None,
) -> dict:
    """获取题目详情，可按 problem_id 或 problem_number 查找"""
    if problem_id is not None:
        problem = db.query(Problem).filter(Problem.problem_id == problem_id).first()
    elif problem_number is not None:
        problem = db.query(Problem).filter(Problem.problem_number == problem_number).first()
    else:
        raise not_found("题目")
    if not problem:
        raise not_found("题目")

    if not can_access_problem(current_user, problem):
        raise not_found("题目不存在或尚未审核通过")

    # 获取标签
    tags = (
        db.query(Tag)
        .join(TagProblem, Tag.tag_id == TagProblem.tag_id)
        .filter(TagProblem.problem_id == problem.problem_id)
        .all()
    )

    # 获取上传者信息
    uploader = db.query(User).filter(User.user_id == problem.uploader_id).first()

    # 当前用户的解题状态
    user_status = {}
    if current_user:
        solved = db.query(UserAcceptedProblem).filter(
            UserAcceptedProblem.user_id == current_user.user_id,
            UserAcceptedProblem.problem_id == problem_id,
        ).first()
        user_status["is_solved"] = solved is not None

        last_sub = (
            db.query(Submission)
            .filter(
                Submission.user_id == current_user.user_id,
                Submission.problem_id == problem_id,
                Submission.is_test_run == 0,
            )
            .order_by(Submission.submitted_at.desc())
            .first()
        )
        user_status["last_submission_status"] = last_sub.status if last_sub else None
    else:
        user_status = {"is_solved": False, "last_submission_status": None}

    from app.utils.file_utils import has_pending_data, list_test_roots

    return {
        "problem_id": problem.problem_id,
        "problem_number": problem.problem_number,
        "problem_name": problem.problem_name,
        "problem_type": problem.problem_type,
        "problem_status": problem.problem_status,
        "has_pending_data": has_pending_data(problem.problem_id),
        "test_cases": list_test_roots(problem.problem_id),
        "is_new_problem": problem.problem_status == "pending_new",
        "difficulty": problem.difficulty,
        "time_limit": problem.time_limit,
        "memory_limit": problem.memory_limit,
        "statement": problem.statement,
        "source": problem.source,
        "sample_download_policy": problem.sample_download_policy,
        "tags": [t.tag_name for t in tags],
        "uploader": {
            "user_id": uploader.user_id if uploader else None,
            "username": uploader.username if uploader else None,
        },
        "statistics": {
            "submissions_before_accepted": problem.submissions_before_accepted,
            "accepted_user_count": problem.accepted_user_count,
        },
        "created_at": problem.created_at.isoformat() if problem.created_at else None,
        "updated_at": problem.updated_at.isoformat() if problem.updated_at else None,
        "user_status": user_status,
    }


def list_problems(
    db: Session,
    page: int, size: int,
    current_user: Optional[User] = None,
    keyword: Optional[str] = None,
    difficulty_min: Optional[int] = None,
    difficulty_max: Optional[int] = None,
    problem_type: Optional[str] = None,
    tag_id: Optional[int] = None,
    status: Optional[str] = None,
    review_mode: bool = False,
    hide_solved: bool = False,
    sort_by: str = "problem_number",
    sort_order: str = "asc",
) -> Tuple[list, int]:
    """分页查询题目列表。管理员可见所有状态，普通用户仅见公开。"""
    is_admin = current_user and ROLE_LEVEL[current_user.role] <= ROLE_LEVEL["admin"]

    if review_mode and is_admin:
        query = db.query(Problem).filter(Problem.problem_status.in_(["pending_new", "pending_modify"]))
    elif is_admin and status:
        query = db.query(Problem).filter(Problem.problem_status == status)
    elif is_admin:
        query = db.query(Problem)
    else:
        query = db.query(Problem).filter(Problem.problem_status.in_(["approved", "pending_modify"]))

    # 隐藏已通过题目
    if hide_solved and current_user:
        solved_ids = db.query(UserAcceptedProblem.problem_id).filter(
            UserAcceptedProblem.user_id == current_user.user_id
        ).subquery()
        query = query.filter(~Problem.problem_id.in_(solved_ids))

    # 筛选
    if keyword:
        if keyword.startswith("#") and keyword[1:].isdigit():
            # #{id} → 按 problem_id 搜
            pid = int(keyword[1:])
            query = query.filter(or_(Problem.problem_name.contains(keyword), Problem.problem_id == pid))
        elif keyword.isdigit():
            # 纯数字 → 按题号或题名搜
            query = query.filter(or_(Problem.problem_name.contains(keyword), Problem.problem_number == int(keyword)))
        else:
            query = query.filter(Problem.problem_name.contains(keyword))
    if difficulty_min is not None:
        query = query.filter(Problem.difficulty >= difficulty_min)
    if difficulty_max is not None:
        query = query.filter(Problem.difficulty <= difficulty_max)
    if problem_type:
        query = query.filter(Problem.problem_type == problem_type)
    if tag_id is not None:
        query = query.join(TagProblem, Problem.problem_id == TagProblem.problem_id) \
                     .filter(TagProblem.tag_id == tag_id)

    # 排序
    sort_map = {
        "problem_number": Problem.problem_number,
        "created_at": Problem.created_at,
        "difficulty": Problem.difficulty,
        "accepted_count": Problem.accepted_user_count,
    }
    sort_col = sort_map.get(sort_by, Problem.problem_number)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    total = query.count()
    problems = query.offset((page - 1) * size).limit(size).all()

    # 批量获取标签
    problem_ids = [p.problem_id for p in problems]
    tag_map: dict[int, list] = {}
    if problem_ids:
        tag_rows = (
            db.query(TagProblem.problem_id, Tag.tag_name)
            .join(Tag, Tag.tag_id == TagProblem.tag_id)
            .filter(TagProblem.problem_id.in_(problem_ids))
            .all()
        )
        for pid, tname in tag_rows:
            tag_map.setdefault(pid, []).append(tname)

    # 批量获取当前用户已通过的题目（使用视图）
    solved_set: set[int] = set()
    if current_user and problem_ids:
        from app.models.views import VUserSolved
        solved_rows = (
            db.query(VUserSolved.problem_id)
            .filter(VUserSolved.user_id == current_user.user_id,
                    VUserSolved.problem_id.in_(problem_ids))
            .all()
        )
        solved_set = {row[0] for row in solved_rows}

    items = []
    for p in problems:
        items.append({
            "problem_id": p.problem_id,
            "problem_number": p.problem_number,
            "problem_name": p.problem_name,
            "problem_status": p.problem_status,
            "difficulty": p.difficulty,
            "problem_type": p.problem_type,
            "time_limit": p.time_limit,
            "memory_limit": p.memory_limit,
            "tags": tag_map.get(p.problem_id, []),
            "submission_count": p.submissions_before_accepted,
            "accepted_user_count": p.accepted_user_count,
            "uploader_id": p.uploader_id,
            "is_solved": p.problem_id in solved_set,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return items, total


def create_problem(
    db: Session,
    uploader: User,
    problem_name: str,
    statement: str,
    problem_type: str,
    difficulty: int,
    time_limit: int,
    memory_limit: int,
    sample_download_policy: str,
    source: Optional[str] = None,
    tags: Optional[List] = None,
) -> Problem:
    """创建题目。tags 可为 int(ID) 或 str(名称) 的列表。"""
    now = datetime.utcnow()

    problem = Problem(
        uploader_id=uploader.user_id,
        problem_status="pending_new",
        problem_name=problem_name,
        statement=statement,
        problem_type=problem_type,
        difficulty=difficulty,
        time_limit=time_limit,
        memory_limit=memory_limit,
        sample_download_policy=sample_download_policy,
        source=source,
        created_at=now,
        updated_at=now,
    )

    db.add(problem)
    db.flush()  # 获取 problem_id

    # 关联标签
    if tags:
        _set_problem_tags(db, problem.problem_id, _resolve_tags(db, tags))

    db.commit()
    db.refresh(problem)
    return problem


def update_problem(
    db: Session,
    problem_id: int,
    current_user: User,
    updates: dict,
    has_test_data: bool = False,
) -> Problem:
    """修改题目"""
    problem = db.query(Problem).filter(Problem.problem_id == problem_id).first()
    if not problem:
        raise not_found("题目")

    # 权限检查
    is_admin = ROLE_LEVEL[current_user.role] <= ROLE_LEVEL["admin"]
    if current_user.user_id != problem.uploader_id and not is_admin:
        raise forbidden("无权限修改该题目")

    # 题型不可修改
    updates.pop("problem_type", None)

    now = datetime.utcnow()

    # 更新字段
    for key, value in updates.items():
        if key == "tags":
            _set_problem_tags(db, problem_id, _resolve_tags(db, value))
        elif hasattr(problem, key) and value is not None:
            setattr(problem, key, value)

    # 被拒绝的题目重新提交 → 待审核
    if problem.problem_status == "rejected":
        problem.problem_status = "pending_new"
        problem.updated_at = now
    # 已通过题目修改测试数据 → 重新审核
    elif has_test_data and problem.problem_status == "approved":
        problem.problem_status = "pending_modify"
        problem.updated_at = now

    problem.updated_at = now
    db.commit()
    db.refresh(problem)
    return problem


def delete_problem(db: Session, problem_id: int, current_user: User) -> None:
    """删除题目"""
    problem = db.query(Problem).filter(Problem.problem_id == problem_id).first()
    if not problem:
        raise not_found("题目")

    is_admin = ROLE_LEVEL[current_user.role] <= ROLE_LEVEL["admin"]

    if not is_admin:
        # 普通用户只能删除未公开的题目
        if problem.uploader_id != current_user.user_id:
            raise forbidden("无权限删除该题目")
        if problem.problem_status in ("approved", "frozen", "archived"):
            raise forbidden("已公开的题目不可删除，请联系管理员")

    # 删除关联数据（提交记录保留，不级联删除）
    db.query(UserAcceptedProblem).filter(UserAcceptedProblem.problem_id == problem_id).delete()
    db.query(TagProblem).filter(TagProblem.problem_id == problem_id).delete()
    db.delete(problem)
    db.commit()

    # 删除文件（失败不影响主流程）
    from app.utils.file_utils import delete_problem_data
    try:
        delete_problem_data(problem_id)
    except Exception:
        pass


def _resolve_tags(db: Session, tags: List) -> List[int]:
    """解析标签列表：int 直接当 ID，str 按名称查找或创建。
    限制：最多 6 个标签，每个标签名不超过 12 字符。"""
    # 过滤空值
    names = [t.strip() if isinstance(t, str) else t for t in tags]
    names = [n for n in names if n != '']
    if len(names) > 6:
        raise bad_request("标签数量不能超过 6 个")
    for n in names:
        if isinstance(n, str) and len(n) > 12:
            raise bad_request(f"标签「{n}」长度不能超过 12 个字符")
    result = []
    for t in tags:
        if isinstance(t, int):
            result.append(t)
        elif isinstance(t, str) and t.strip():
            tag = db.query(Tag).filter(Tag.tag_name == t.strip()).first()
            if not tag:
                tag = Tag(tag_name=t.strip(), problems=0)
                db.add(tag)
                db.flush()
            result.append(tag.tag_id)
    return result


def _set_problem_tags_by_name(db: Session, problem_id: int, tag_names: List[str]):
    """按标签名设置标签：已存在的复用，不存在的自动创建"""
    tag_ids = []
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        tag = db.query(Tag).filter(Tag.tag_name == name).first()
        if not tag:
            tag = Tag(tag_name=name, problems=0)
            db.add(tag)
            db.flush()
        tag_ids.append(tag.tag_id)
    _set_problem_tags(db, problem_id, tag_ids)


def _set_problem_tags(db: Session, problem_id: int, tag_ids: List[int]):
    """设置题目的标签（先删后插）"""
    db.query(TagProblem).filter(TagProblem.problem_id == problem_id).delete()
    for tid in tag_ids:
        db.add(TagProblem(tag_id=tid, problem_id=problem_id))

    # 更新 Tags.problems 冗余计数
    for tid in tag_ids:
        count = db.query(TagProblem).filter(TagProblem.tag_id == tid).count()
        db.query(Tag).filter(Tag.tag_id == tid).update({"problems": count})
    db.flush()
