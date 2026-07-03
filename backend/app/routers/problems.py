"""题目通用接口 + 题目编辑接口"""
import json
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, get_optional_user, require_role, PaginationParams, ROLE_LEVEL
from app.models.user import User
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.notification import Notification
from app.services import problem_service
from app.utils.response import success, error, paginated
from app.utils.file_utils import save_test_data, save_problem_images, remove_test_files
from app.config import MAX_CODE_LENGTH

router = APIRouter()


# ============================================================
# 3.1 获取题目列表
# ============================================================
@router.get("")
def list_problems(
    keyword: Optional[str] = Query(None),
    difficulty_min: Optional[int] = Query(None),
    difficulty_max: Optional[int] = Query(None),
    problem_type: Optional[str] = Query(None),
    tag_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    review_mode: bool = Query(False),
    hide_solved: bool = Query(False),
    sort_by: str = Query("problem_number"),
    sort_order: str = Query("asc"),
    pagination: PaginationParams = Depends(),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    try:
        items, total = problem_service.list_problems(
            db, pagination.page, pagination.size,
            current_user=current_user,
            keyword=keyword,
            difficulty_min=difficulty_min,
            difficulty_max=difficulty_max,
            problem_type=problem_type,
            tag_id=tag_id,
            status=status,
            review_mode=review_mode,
            hide_solved=hide_solved,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        resp = paginated(items, pagination.page, pagination.size, total)
        # 管理员额外返回各状态待审核数量
        if current_user and ROLE_LEVEL[current_user.role] <= ROLE_LEVEL["admin"]:
            pending_new_count = db.query(Problem).filter(
                Problem.problem_status == "pending_new"
            ).count() or 0
            pending_modify_count = db.query(Problem).filter(
                Problem.problem_status == "pending_modify"
            ).count() or 0
            resp["data"]["review_count"] = pending_new_count + pending_modify_count
            resp["data"]["pending_new_count"] = pending_new_count
            resp["data"]["pending_modify_count"] = pending_modify_count
        return resp
    except Exception as e:
        return error(message=str(e))


# ============================================================
# 3.3 获取题目详情
# ============================================================
@router.get("/{identifier}")
def get_problem_detail(
    identifier: str,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    try:
        # p5 → problem_id=5, 1001 → problem_number=1001
        if identifier.startswith("p") and identifier[1:].isdigit():
            data = problem_service.get_problem_detail(db, problem_id=int(identifier[1:]), current_user=current_user)
        elif identifier.isdigit():
            data = problem_service.get_problem_detail(db, problem_number=int(identifier), current_user=current_user)
        else:
            return error(message="无效的题目标识")
        return success(data=data)
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 3.4 提交代码（正式评测）
# ============================================================
@router.post("/{problem_id}/submit")
def submit_code(
    problem_id: int,
    code: str = Form(..., description="源代码"),
    language: str = Form(..., description="编程语言"),
    use_pending: bool = Form(False, description="使用待审核数据（管理员）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.utils.file_utils import has_pending_data

    problem = db.query(Problem).filter(Problem.problem_id == problem_id).first()
    if not problem:
        return error(message="题目不存在")

    # 权限和状态检查
    is_admin = ROLE_LEVEL[current_user.role] <= ROLE_LEVEL["admin"]
    if use_pending and not is_admin:
        return error(message="无权使用待审核数据")

    if use_pending and not has_pending_data(problem_id):
        return error(message="没有待审核的测试数据")

    can_submit = problem.problem_status in ("approved", "pending_modify") \
        or (is_admin and problem.problem_status == "pending_new")
    if not can_submit:
        return error(message="该题目当前不可提交")

    if len(code) > MAX_CODE_LENGTH:
        return error(message=f"代码过长，最大 {MAX_CODE_LENGTH} 字符")

    if language not in ("cpp", "python3"):
        return error(message="暂仅支持 cpp 和 python3")

    now = datetime.utcnow()
    submission = Submission(
        user_id=current_user.user_id,
        username=current_user.username,
        problem_id=problem_id,
        problem_number=problem.problem_number,
        problem_name=problem.problem_name,
        problem_type=problem.problem_type,
        is_test_run=use_pending,
        code=code,
        code_length=len(code.encode("utf-8")),
        language=language,
        status="pending",
        submitted_at=now,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return success(
        data={"submission_id": submission.submission_id, "status": "pending"},
        message="提交成功，正在评测",
    )


# ============================================================
# 3.5 代码调试（自定义测试）
# ============================================================
@router.post("/{problem_id}/debug")
async def debug_code(
    problem_id: int,
    code: str = Form(..., description="源代码"),
    language: str = Form(..., description="编程语言"),
    input_data: str = Form("", description="自定义输入"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    problem = db.query(Problem).filter(Problem.problem_id == problem_id).first()
    if not problem:
        return error(message="题目不存在")

    if language not in ("cpp", "python3"):
        return error(message="暂仅支持 cpp 和 python3")

    if len(code) > MAX_CODE_LENGTH:
        return error(message=f"代码过长，最大 {MAX_CODE_LENGTH} 字符")

    # 调试直接调评测机，不创建提交记录
    from app.models.judge_state import JudgeState
    from app.config import JUDGE_SERVER_URL
    state = db.query(JudgeState).first()
    if not state or not state.is_connected:
        return error(message="评测机未连接，无法调试")
    if state.last_heartbeat:
        if (datetime.utcnow() - state.last_heartbeat).total_seconds() > 30:
            return error(message="评测机已离线，无法调试")

    import httpx
    time_limit_ms = problem.time_limit or 2000
    memory_limit_kb = problem.memory_limit or 256000

    from app.services.judge_service import _pending_jobs
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{JUDGE_SERVER_URL}/judge", data={
                "code": code,
                "language": language,
                "problem_id": str(problem_id),
                "time_limit_ms": str(time_limit_ms),
                "memory_limit_kb": str(memory_limit_kb),
                "is_debug": "true",
                "debug_input": input_data,
            })
            if resp.status_code != 200:
                return error(message=f"评测机返回错误: {resp.status_code}")
            job = resp.json()
            job_id = job.get("job_id")
            if not job_id:
                return error(message="评测机未返回任务ID")
    except Exception as e:
        return error(message=f"调评测机失败: {e}")

    # 注册到调度器，由轮询统一获取结果（负数 sub_id 标记为调试）
    _pending_jobs[job_id] = -1

    return success(
        data={"job_id": job_id},
        message="调试请求已提交",
    )


# ============================================================
# 3.5b 获取调试结果
# ============================================================
@router.get("/debug/result/{job_id}")
def get_debug_result(job_id: str, current_user: User = Depends(get_current_user)):
    from app.services.judge_service import _debug_results, _pending_jobs
    result = _debug_results.get(job_id)
    if result:
        del _debug_results[job_id]
        first_test = (result.get("tests") or [{}])[0]
        summary = result.get("summary", {})
        s = summary.get("status", "")
        if s == "Accepted": mapped = "ok"
        elif "compile" in s.lower(): mapped = "compile_error"
        elif "Time" in s: mapped = "time_limit_exceeded"
        elif "Memory" in s: mapped = "memory_limit_exceeded"
        elif "System" in s: mapped = "system_error"
        else: mapped = "runtime_error"
        compile_info = result.get("compile", {})
        return success(data={
            "output": first_test.get("program_output", ""),
            "error": first_test.get("message", ""),
            "run_time": result.get("run_time", 0),
            "run_memory": result.get("run_memory", 0),
            "status": mapped,
            "compile_error": compile_info.get("output") if isinstance(compile_info, dict) else result.get("compile_output"),
        })
    if job_id in _pending_jobs:
        # 检查评测机是否已断开
        from app.models.judge_state import JudgeState
        state = db.query(JudgeState).first()
        if not state or not state.is_connected:
            return success(data={"status": "system_error", "error": "评测机已断开连接"})
        return success(data={"status": "pending"})
    return success(data={"status": "system_error", "error": "任务丢失或评测机离线"})


# 4.1 创建题目
# ============================================================
@router.post("")
async def create_problem(
    problem_name: str = Form(...),
    statement: str = Form(...),
    problem_type: str = Form(...),
    difficulty: int = Form(...),
    time_limit: int = Form(...),
    memory_limit: int = Form(...),
    sample_download_policy: str = Form("none"),
    source: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    test_data: List[UploadFile] = File([]),
    images: List[UploadFile] = File([]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        tag_list = json.loads(tags) if tags else None

        problem = problem_service.create_problem(
            db, current_user,
            problem_name=problem_name,
            statement=statement,
            problem_type=problem_type,
            difficulty=difficulty,
            time_limit=time_limit,
            memory_limit=memory_limit,
            sample_download_policy=sample_download_policy,
            source=source,
            tags=tag_list,
        )

        # 保存测试数据
        if test_data:
            save_test_data(test_data, problem.problem_id, problem_type)

        # 保存题面图片
        if images:
            save_problem_images(images, problem.problem_id)

        return success(
            data={
                "problem_id": problem.problem_id,
                "problem_number": problem.problem_number,
                "problem_status": problem.problem_status,
            },
            message="上传成功，等待管理员审核",
        )
    except ValueError as e:
        return error(message=str(e))
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 4.2 修改题目
# ============================================================
@router.put("/{problem_id}")
async def update_problem(
    problem_id: int,
    problem_name: Optional[str] = Form(None),
    statement: Optional[str] = Form(None),
    difficulty: Optional[int] = Form(None),
    time_limit: Optional[int] = Form(None),
    memory_limit: Optional[int] = Form(None),
    sample_download_policy: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    test_data: List[UploadFile] = File([]),
    excluded_roots: Optional[str] = Form(None),
    images: List[UploadFile] = File([]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        import json as _json
        updates = {}
        if problem_name is not None:
            updates["problem_name"] = problem_name
        if statement is not None:
            updates["statement"] = statement
        if difficulty is not None:
            updates["difficulty"] = difficulty
        if time_limit is not None:
            updates["time_limit"] = time_limit
        if memory_limit is not None:
            updates["memory_limit"] = memory_limit
        if sample_download_policy is not None:
            updates["sample_download_policy"] = sample_download_policy
        if source is not None:
            updates["source"] = source
        if tags is not None:
            updates["tags"] = _json.loads(tags)

        has_test = len(test_data) > 0
        excluded = _json.loads(excluded_roots) if excluded_roots else []

        # 公开题被修改样例 → 先复制旧数据到 pending，再合并新数据
        if has_test or excluded:
            from app.utils.file_utils import copy_approved_to_pending
            copy_approved_to_pending(problem_id, excluded)

        problem = problem_service.update_problem(db, problem_id, current_user, updates, has_test or bool(excluded))

        # 管理员编辑他人题目时通知原作者
        if current_user.user_id != problem.uploader_id:
            db.add(Notification(
                user_id=problem.uploader_id,
                title="题目被编辑",
                content=f"管理员「{current_user.username}」编辑了您的题目「{problem.problem_name}」。",
                created_at=datetime.utcnow(),
            ))
            db.commit()

        if test_data:
            save_test_data(test_data, problem_id, problem.problem_type, append=True)

        if images:
            save_problem_images(images, problem_id)

        return success(
            data={
                "problem_id": problem.problem_id,
                "problem_name": problem.problem_name,
                "difficulty": problem.difficulty,
                "problem_status": problem.problem_status,
                "updated_at": problem.updated_at.isoformat() if problem.updated_at else None,
            },
            message="修改成功，测试数据已更新，需等待管理员重新审核" if has_test else "修改成功",
        )
    except ValueError as e:
        return error(message=str(e))
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


# ============================================================
# 4.2b 删除测试样例文件
# ============================================================
@router.delete("/{problem_id}/testdata/{root}")
def delete_test_case(
    problem_id: int,
    root: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        remove_test_files(problem_id, [root])
        return success(message=f"已删除样例 {root}")
    except Exception as e:
        return error(message=str(e))


# ============================================================
# 4.3 删除题目
# ============================================================
@router.delete("/{problem_id}")
def delete_problem(
    problem_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        problem_service.delete_problem(db, problem_id, current_user)
        return success(message="删除成功")
    except Exception as e:
        if hasattr(e, 'status_code'):
            return error(message=e.detail)
        return error(message=str(e))


