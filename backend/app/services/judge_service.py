"""
评测调度器 —— 轮询 DB pending 提交，HTTP 调评测机（异步任务模式）。
"""
import asyncio
import json
import os
from datetime import datetime

import httpx

from sqlalchemy.orm import Session

from app.config import JUDGE_POLL_INTERVAL_SECONDS, JUDGE_SERVER_URL, PROBLEMS_DATA_DIR, PROBLEMS_PENDING_DIR
from app.models.submission import Submission, UserAcceptedProblem
from app.models.user import User
from app.models.problem import Problem
from app.models.judge_state import JudgeState


STATUS_MAP = {
    "Accepted": "accepted", "Presentation Error": "presentation_error",
    "Wrong Answer": "wrong_answer", "Time Limit Exceeded": "time_limit_exceeded",
    "Memory Limit Exceeded": "memory_limit_exceeded", "Runtime Error": "runtime_error",
    "Compile Error": "compile_error", "System Error": "system_error",
}

# 已提交到评测机的 job_id → submission_id 映射
_pending_jobs: dict[str, int] = {}
# 调试任务的结果: job_id → result dict
_debug_results: dict[str, dict] = {}
# 延迟文件操作: problem_id → (action, args)  等待该题 running 清零后执行
_deferred_ops: dict[int, tuple] = {}
# 中间结果缓存（内存，不写 DB）: submission_id → (result_dict, last_test_count)
_partial_cache: dict[int, tuple] = {}

def get_partial_result(submission_id: int) -> dict | None:
    """供 API 层读取中间评测结果"""
    entry = _partial_cache.get(submission_id)
    return entry[0] if entry else None


def defer_file_op(problem_id: int, action: str, *args):
    """延迟文件操作：等该题 running 清零后执行"""
    _deferred_ops[problem_id] = (action, args)


def _try_execute_deferred(db: Session):
    """检查并执行延迟的文件操作"""
    from app.utils.file_utils import approve_test_data, reject_test_data
    done = []
    for pid, (action, args) in list(_deferred_ops.items()):
        running = db.query(Submission).filter(
            Submission.problem_id == pid, Submission.status == "running"
        ).count()
        if running == 0:
            try:
                if action == "approve":
                    approve_test_data(pid)
                elif action == "reject":
                    reject_test_data(pid, *args)
            except Exception as e:
                print(f"[DeferredOp] {action} pid={pid} 失败: {e}")
            done.append(pid)
    for pid in done:
        del _deferred_ops[pid]


class JudgeDispatcher:
    def __init__(self, db_session_factory):
        self.db_factory = db_session_factory
        self.poll_interval = JUDGE_POLL_INTERVAL_SECONDS
        self._running = False

    def stop(self):
        self._running = False

    async def start(self):
        self._running = True
        print(f"[JudgeDispatch] 启动，评测机 {JUDGE_SERVER_URL}")
        while self._running:
            try:
                await self._poll()
                await self._check_pending_jobs()
            except Exception as e:
                print(f"[JudgeDispatch] 异常: {e}")
            await asyncio.sleep(self.poll_interval)

    async def _poll(self):
        """取一条 pending 提交，发给评测机"""
        db: Session = self.db_factory()
        try:
            # 先尝试执行延迟的文件操作
            _try_execute_deferred(db)

            state = db.query(JudgeState).first()
            if not state or not state.is_connected:
                return
            if state.last_heartbeat:
                age = (datetime.utcnow() - state.last_heartbeat).total_seconds()
                if age > 30:
                    return

            # 跳过有延迟文件操作待执行的题目的提交
            deferred_pids = set(_deferred_ops.keys())
            query = db.query(Submission).filter(Submission.status == "pending")
            if deferred_pids:
                query = query.filter(~Submission.problem_id.in_(deferred_pids))
            sub = (
                query.order_by(Submission.is_test_run.desc(), Submission.submitted_at.asc())
                .with_for_update(skip_locked=True)
                .first()
            )
            if not sub:
                return

            sub.status = "running"
            db.commit()

            # 取出评测所需数据后立即释放 DB 连接
            sub_id = sub.submission_id
            code = sub.code
            language = sub.language
            problem_id = sub.problem_id
            is_test_run = sub.is_test_run
        finally:
            db.close()

        # 查题目信息（短连接）
        problem = None
        db2: Session = self.db_factory()
        try:
            problem = db2.query(Problem).filter(Problem.problem_id == problem_id).first()
        finally:
            db2.close()

        # HTTP 调评测机（不持有 DB 连接）
        job_id = await self._submit_to_judge_http(code, language, problem_id,
            problem.time_limit if problem else 1000,
            problem.memory_limit if problem else 256000,
            is_test_run)

        if job_id:
            # 写初始占位结果到内存
            self._write_initial_placeholder(sub_id, problem_id, is_test_run)
            _pending_jobs[job_id] = sub_id
        else:
            # 评测机提交失败 → 回退为 pending
            db3: Session = self.db_factory()
            try:
                sub = db3.query(Submission).filter(Submission.submission_id == sub_id).first()
                if sub and sub.status == "running":
                    sub.status = "pending"
                    db3.commit()
            finally:
                db3.close()

    async def _submit_to_judge_http(self, code, language, problem_id, time_limit, memory_limit, is_test_run) -> str | None:
        data = {
            "code": code,
            "language": language,
            "problem_id": str(problem_id),
            "time_limit_ms": str(time_limit),
            "memory_limit_kb": str(memory_limit),
            "is_test_run": str(is_test_run),
        }

        base_dir = PROBLEMS_PENDING_DIR if is_test_run else PROBLEMS_DATA_DIR
        test_dir = base_dir / str(problem_id)
        files = []
        if test_dir.exists() and test_dir.is_dir():
            for fname in os.listdir(test_dir):
                fpath = test_dir / fname
                if fpath.is_file():
                    files.append(("test_data", (fname, open(fpath, "rb"), "application/octet-stream")))

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{JUDGE_SERVER_URL}/judge", data=data, files=files)
                if resp.status_code == 200:
                    return resp.json().get("job_id")
        except Exception as e:
            print(f"[JudgeDispatch] 提交失败 problem={problem_id}: {e}")
        finally:
            for _, (_, f, _) in files:
                try: f.close()
                except Exception: pass
        return None

    def _write_initial_placeholder(self, submission_id: int, problem_id: int, is_test_run: bool):
        """写入全 Pending 占位结果到内存（发评测机后立即调用，前端首次轮询即可渲染网格）"""
        base_dir = PROBLEMS_PENDING_DIR if is_test_run else PROBLEMS_DATA_DIR
        test_dir = base_dir / str(problem_id)
        test_roots = sorted(set(
            os.path.splitext(fname)[0] for fname in os.listdir(test_dir)
            if os.path.splitext(fname)[1].lower() in ('.in', '.out', '.ans')
        )) if test_dir.exists() and test_dir.is_dir() else []
        if not test_roots:
            return
        initial = [{"name": r, "status": "Pending", "time_used": None, "memory_used_kb": 0} for r in test_roots]
        _partial_cache[submission_id] = ({"tests": initial, "run_time": 0, "run_memory": 0}, 0)

    async def _check_pending_jobs(self):
        """检查已提交的 job，回写完成结果或 running 时的中间结果"""
        if not _pending_jobs:
            return

        # 若已断开，不再接收评测机结果
        db: Session = self.db_factory()
        try:
            from app.models.judge_state import JudgeState
            state = db.query(JudgeState).first()
            if not state or not state.is_connected:
                _pending_jobs.clear()
                return
        finally:
            db.close()

        done_ids = []
        for job_id, sub_id in list(_pending_jobs.items()):
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{JUDGE_SERVER_URL}/job/{job_id}")
                    if resp.status_code == 200:
                        data = resp.json()
                        result = data.get("result")
                        if data["status"] == "done":
                            result = result or {}
                            if sub_id < 0:
                                _debug_results[job_id] = result
                            else:
                                self._write_result(sub_id, result)
                                # 终态结果也写入缓存，覆盖中间状态
                                tests = result.get("tests", [])
                                _partial_cache[sub_id] = ({"tests": tests, "run_time": result.get("run_time", 0), "run_memory": result.get("run_memory", 0)}, len(tests))
                            done_ids.append(job_id)
                        elif data["status"] == "running" and result and result.get("tests"):
                            if sub_id > 0:
                                self._write_partial(sub_id, result)  # 仅写内存
                    elif resp.status_code == 404:
                        done_ids.append(job_id)
            except Exception:
                pass

        for jid in done_ids:
            _pending_jobs.pop(jid, None)
            if jid in _debug_results:
                pass  # 保留供 SSE 读取

    def _write_partial(self, submission_id: int, result: dict):
        """缓存中间结果到内存（不写 DB，避免 NVARCHAR(MAX) 频繁更新拖慢整表）"""
        tests = result.get("tests", [])
        done = sum(1 for t in tests if t.get("status") != "Pending")
        last = _partial_cache.get(submission_id, (None, 0))[1]
        if done > last:
            run_time = int(max((t.get("time_used") or 0 for t in tests)) * 1000) if tests else 0
            run_memory = int(max((t.get("memory_used_kb") or 0 for t in tests))) if tests else 0
            _partial_cache[submission_id] = ({"tests": tests, "run_time": run_time, "run_memory": run_memory}, done)

    def _write_result(self, submission_id: int, result: dict):
        db: Session = self.db_factory()
        try:
            # 若已断开连接，不写回结果
            from app.models.judge_state import JudgeState
            state = db.query(JudgeState).first()
            if not state or not state.is_connected:
                return

            sub = db.query(Submission).filter(Submission.submission_id == submission_id).first()
            if not sub or sub.status != "running":
                return

            now = datetime.utcnow()
            summary = result.get("summary", {})
            tests = result.get("tests", [])

            sub.status = STATUS_MAP.get(summary.get("status", "System Error"), "system_error")
            sub.judged_result = json.dumps(result, ensure_ascii=False)
            sub.judged_at = now

            if tests:
                sub.run_time = int(max((t.get("time_used") or 0 for t in tests)) * 1000)
                sub.run_memory = int(max((t.get("memory_used_kb") or 0 for t in tests)))

            if sub.is_test_run == 0:
                problem = db.query(Problem).filter(Problem.problem_id == sub.problem_id).first()
                user = db.query(User).filter(User.user_id == sub.user_id).first()
                already_solved = db.query(UserAcceptedProblem).filter(
                    UserAcceptedProblem.user_id == sub.user_id,
                    UserAcceptedProblem.problem_id == sub.problem_id,
                ).first() is not None
                if not already_solved:
                    if problem:
                        problem.submissions_before_accepted += 1
                    if user:
                        user.total_submissions += 1
                if sub.status == "accepted":
                    existing = (
                        db.query(UserAcceptedProblem)
                        .filter(UserAcceptedProblem.user_id == sub.user_id,
                                UserAcceptedProblem.problem_id == sub.problem_id)
                        .first()
                    )
                    if not existing:
                        db.add(UserAcceptedProblem(
                            user_id=sub.user_id, problem_id=sub.problem_id, first_accepted_at=now,
                        ))
                        if user:
                            user.solved_problems += 1
                        if problem:
                            problem.accepted_user_count += 1

            db.commit()
        finally:
            db.close()