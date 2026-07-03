"""管理员接口路由"""
import json
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.dependencies import get_current_user, require_role, PaginationParams, ROLE_LEVEL
from app.models.user import User
from app.models.problem import Problem
from app.models.notification import Notification
from app.models.submission import Submission
from app.models.judge_state import JudgeState
from app.utils.response import success, error, paginated

ROLE_LABEL = {"root": "站长", "admin": "管理员", "user": "普通用户"}

router = APIRouter()


# ============================================================
# 2.1 获取用户列表（管理员）
# ============================================================
@router.get("/users")
def list_users(
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    if keyword:
        query = query.filter(User.username.contains(keyword))

    total = query.count()
    users = query.order_by(User.user_id.asc()) \
                 .offset(pagination.offset).limit(pagination.size).all()

    return paginated(
        [
            {
                "user_id": u.user_id,
                "username": u.username,
                "role": u.role,
                "status": u.status,
                "solved_problems": u.solved_problems,
                "total_submissions": u.total_submissions,
                "registered_at": u.registered_at.isoformat() if u.registered_at else None,
            }
            for u in users
        ],
        pagination.page, pagination.size, total,
    )


# ============================================================
# 2.2 修改用户角色（站长专用）
# ============================================================
@router.put("/users/{user_id}/role")
def change_user_role(
    user_id: int,
    role: str = Query(...),
    current_user: User = Depends(require_role("root")),
    db: Session = Depends(get_db),
):
    if current_user.user_id == user_id:
        return error(message="不可修改自己的角色")

    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        return error(message="用户不存在")

    if role not in ("admin", "user"):
        return error(message="无效的角色；站长唯一且不可转让")

    # 不可将最后一个 root 降级
    if target.role == "root":
        root_count = db.query(func.count(User.user_id)).filter(User.role == "root").scalar()
        if root_count <= 1:
            return error(message="不可将系统中最后一个站长降级")

    old_label = ROLE_LABEL.get(target.role, target.role)
    target.role = role
    new_label = ROLE_LABEL.get(role, role)

    # 发送通知
    db.add(Notification(
        user_id=target.user_id,
        title="角色变更通知",
        content=f"您的账号角色已被站长由「{old_label}」变更为「{new_label}」。",
        created_at=datetime.utcnow(),
    ))

    db.commit()

    return success(
        data={"user_id": target.user_id, "username": target.username, "role": target.role},
        message="角色修改成功",
    )


# ============================================================
# 2.3 封禁/解封用户（管理员及以上）
# ============================================================
@router.put("/users/{user_id}/status")
def change_user_status(
    user_id: int,
    status: str = Query(...),
    reason: Optional[str] = Query(None),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if current_user.user_id == user_id:
        return error(message="不可修改自己的状态")

    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        return error(message="用户不存在")

    if status not in ("active", "banned"):
        return error(message="无效的状态")

    # 不可封禁权限不低于自己的用户
    if ROLE_LEVEL[current_user.role] >= ROLE_LEVEL[target.role]:
        return error(message="无权封禁权限不低于自己的用户")

    target.status = status
    if status == "banned":
        target.token_version += 1

    # 发送通知
    reason_text = f"，原因：{reason}" if reason else ""
    if status == "banned":
        title = "账号封禁通知"
        content = f"您的账号已被管理员封禁{reason_text}。如有疑问，请联系管理员。"
    else:
        title = "账号解封通知"
        content = "您的账号已被管理员解封，现已恢复正常使用。"
    db.add(Notification(
        user_id=target.user_id,
        title=title,
        content=content,
        created_at=datetime.utcnow(),
    ))

    db.commit()

    return success(
        data={"user_id": target.user_id, "username": target.username, "status": target.status},
        message="用户已封禁" if status == "banned" else "用户已解封",
    )


# ============================================================
# 4.4 更改题目状态（管理员审核）
# ============================================================
@router.put("/problems/{problem_id}/status")
def change_problem_status(
    problem_id: int,
    status: str = Query(...),
    review_comment: Optional[str] = Query(None),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    problem = db.query(Problem).filter(Problem.problem_id == problem_id).first()
    if not problem:
        return error(message="题目不存在")

    # 不可设为 draft 或 pending
    if status in ("pending_new", "pending_modify"):
        return error(message="不可将题目设为待审核状态")

    valid_statuses = ("approved", "rejected", "frozen", "archived")
    if status not in valid_statuses:
        return error(message=f"无效的状态，可选值: {', '.join(valid_statuses)}")

    now = datetime.utcnow()
    prev_status = problem.problem_status

    # pending_modify 被拒绝 → 退回公开状态
    if status == "rejected" and prev_status == "pending_modify":
        problem.problem_status = "approved"
    else:
        problem.problem_status = status

    problem.reviewer_id = current_user.user_id
    problem.reviewed_at = now
    problem.updated_at = now

    if review_comment:
        problem.review_comment = review_comment

    # 审核通过时分配编号（若尚未分配）
    if status == "approved" and problem.problem_number is None:
        max_num = db.query(func.max(Problem.problem_number)).scalar()
        problem.problem_number = (max_num or 1000) + 1

    # 发送通知给上传者
    if status in ("approved", "rejected"):
        if status == "approved":
            notify_title = "题目审核通过"
            notify_content = f"您的题目「{problem.problem_name}」已通过审核，现已公开可见。"
        elif prev_status == "pending_modify":
            notify_title = "题目修改被拒绝"
            notify_content = f"您的题目「{problem.problem_name}」的修改申请已被拒绝，题目保持公开状态。"
        else:
            notify_title = "题目审核被拒绝"
            notify_content = f"您的题目「{problem.problem_name}」未通过审核。"
        if review_comment:
            notify_content += f"。审核备注: {review_comment}"
        notification = Notification(
            user_id=problem.uploader_id,
            title=notify_title,
            content=notify_content,
            created_at=now,
        )
        db.add(notification)

    # 审核操作延迟执行：等该题 running 清零后再移动文件
    from app.services.judge_service import defer_file_op
    if status == "approved":
        defer_file_op(problem_id, "approve")
    elif status == "rejected":
        defer_file_op(problem_id, "reject", prev_status == "pending_modify")

    db.commit()

    msg = (
        f"审核通过，已分配编号 {problem.problem_number}" if status == "approved" and problem.problem_number and prev_status != "pending_modify"
        else f"审核通过，保留原编号 {problem.problem_number}" if status == "approved"
        else f"已拒绝修改，题目恢复公开" if status == "rejected" and prev_status == "pending_modify"
        else f"已拒绝该题目" if status == "rejected"
        else f"题目已{'冻结' if status == 'frozen' else '归档'}"
    )

    return success(
        data={
            "problem_id": problem.problem_id,
            "problem_status": problem.problem_status,
            "problem_number": problem.problem_number,
            "reviewed_at": problem.reviewed_at.isoformat() if problem.reviewed_at else None,
            "uploader_notified": status in ("approved", "rejected"),
        },
        message=msg,
    )


# ============================================================
# 5.1 发送消息（管理员/站长）
# ============================================================
@router.post("/notifications")
def send_notification(
    title: str = Query(...),
    content: str = Query(...),
    target_user_id: Optional[int] = Query(None),
    target_username: Optional[str] = Query(None),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()

    target = None
    if target_user_id is not None:
        target = db.query(User).filter(User.user_id == target_user_id).first()
        if not target:
            return error(message="目标用户不存在")
    elif target_username:
        target = db.query(User).filter(User.username == target_username).first()
        if not target:
            return error(message=f"用户「{target_username}」不存在")
    else:
        return error(message="请指定目标用户ID或用户名")

    notif = Notification(
        user_id=target.user_id,
        title=title,
        content=content,
        created_at=now,
    )
    db.add(notif)
    db.commit()

    return success(
        data={"recipient_id": target.user_id, "username": target.username, "created_at": now.isoformat()},
        message=f"消息已发送给用户「{target.username}」",
    )


# ============================================================
# 评测机管理（独立进程）
# ============================================================
import os
import subprocess
import sys
from pathlib import Path

@router.get("/judge")
def get_judge_status(current_user: User = Depends(require_role("admin")),
                     db: Session = Depends(get_db)):
    state = db.query(JudgeState).first()
    if not state:
        return success(data={"running": False, "connected": False, "status": "stopped"})
    running = False
    if state.last_heartbeat:
        age = (datetime.utcnow() - state.last_heartbeat).total_seconds()
        running = age < 10
    return success(data={
        "running": running,
        "connected": state.is_connected,
        "status": state.status if running else "stopped",
    })


@router.post("/judge/connect")
def judge_connect(
    cutoff: Optional[str] = Query(None),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    state = db.query(JudgeState).first()
    if not state:
        state = JudgeState(id=1)
        db.add(state)
        db.commit()
    if not state.last_heartbeat:
        return error(message="评测机未运行")
    age = (datetime.utcnow() - state.last_heartbeat).total_seconds()
    if age > 30:
        return error(message="评测机已离线")
    state.is_connected = True
    rejected = 0
    if cutoff:
        try:
            cutoff_time = datetime.fromisoformat(cutoff)
            now = datetime.utcnow()
            old = (
                db.query(Submission)
                .filter(Submission.status == "pending", Submission.submitted_at < cutoff_time)
                .all()
            )
            for s in old:
                s.status = "rj"
                s.judged_at = now
                s.judged_result = json.dumps({"error": "连接时因早于阈值被拒绝"}, ensure_ascii=False)
            rejected = len(old)
        except ValueError:
            return error(message="无效的时间格式")
    db.commit()
    return success(message=f"已连接，{rejected} 条旧提交被拒绝" if rejected else "已连接评测机")


@router.post("/judge/disconnect")
def judge_disconnect(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    state = db.query(JudgeState).first()
    if state:
        state.is_connected = False
    now = datetime.utcnow()
    affected = (
        db.query(Submission)
        .filter(Submission.status == "running")
        .update({"status": "system_error", "judged_at": now,
                 "judged_result": json.dumps({"error": "OJ 断开连接"}, ensure_ascii=False)},
                synchronize_session=False)
    )
    db.commit()
    return success(message=f"已断开，{affected} 条被中断")
