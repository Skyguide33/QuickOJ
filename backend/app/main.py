"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager
import asyncio
import json
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import engine, Base, SessionLocal
from app.config import IMAGES_DIR, AVATARS_DIR
from app.services.judge_service import JudgeDispatcher


import os
from app.config import JUDGE_SERVER_URL as JUDGE_URL

async def _watchdog():
    """每 2 秒检测评测机 /health，一次失败即断开"""
    import httpx
    while True:
        await asyncio.sleep(2)
        db = SessionLocal()
        try:
            from app.models.judge_state import JudgeState
            from app.models.submission import Submission
            state = db.query(JudgeState).first()
            if not state:
                state = JudgeState(id=1)
                db.add(state)
                db.commit()

            # 主动检测评测机（timeout=10s，容忍评测机繁忙）
            alive = False
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{JUDGE_URL}/health")
                    if resp.status_code == 200:
                        alive = True
                        state.last_heartbeat = datetime.utcnow()
                        state.status = "idle"
                        db.commit()
            except Exception:
                pass

            if alive:
                continue

            # 一次失败即断开
            db.refresh(state)
            if state.is_connected:
                state.is_connected = False
                # 清空待接收的评测机结果
                from app.services.judge_service import _pending_jobs
                _pending_jobs.clear()
                affected = (
                    db.query(Submission)
                    .filter(Submission.status == "running")
                    .update({"status": "system_error", "judged_at": datetime.utcnow(),
                             "judged_result": json.dumps({"error": "评测机离线"}, ensure_ascii=False)},
                            synchronize_session=False)
                )
                db.commit()
                if affected:
                    print(f"[Watchdog] 评测机离线，{affected} 条 running → se")
        except Exception as e:
            print(f"[Watchdog] {e}")
        finally:
            db.close()


async def _timeout_checker():
    """启动时立即扫描 + 每 10 分钟检查超过 10 分钟的 running 提交，标记为 system_error"""
    from datetime import timedelta

    async def _scan():
        db = SessionLocal()
        try:
            from app.models.submission import Submission
            cutoff = datetime.utcnow() - timedelta(minutes=10)
            affected = (
                db.query(Submission)
                .filter(Submission.status == "running",
                        Submission.submitted_at < cutoff)
                .update({"status": "system_error", "judged_at": datetime.utcnow(),
                         "judged_result": json.dumps({"error": "评测超时，系统自动终止"}, ensure_ascii=False)},
                        synchronize_session=False)
            )
            db.commit()
            if affected:
                print(f"[Timeout] {affected} 条 running 超过 10 分钟 → system_error")
        except Exception as e:
            print(f"[Timeout] {e}")
        finally:
            db.close()

    await _scan()  # 启动时立即执行
    while True:
        await asyncio.sleep(600)  # 之后每 10 分钟
        await _scan()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    # 启动时断开所有评测机连接，需管理员手动重连
    db = SessionLocal()
    try:
        from app.models.judge_state import JudgeState
        state = db.query(JudgeState).first()
        if state:
            state.is_connected = False
            db.commit()
    except Exception:
        pass
    finally:
        db.close()

    # 启动评测调度器
    dispatcher = JudgeDispatcher(SessionLocal)
    judge_task = asyncio.create_task(dispatcher.start())
    wd_task = asyncio.create_task(_watchdog())
    timeout_task = asyncio.create_task(_timeout_checker())
    print("[OJ] 评测调度器已启动")

    yield

    dispatcher.stop()
    judge_task.cancel()
    wd_task.cancel()
    timeout_task.cancel()
    try: await judge_task
    except asyncio.CancelledError: pass
    try: await wd_task
    except asyncio.CancelledError: pass
    try: await timeout_task
    except asyncio.CancelledError: pass


app = FastAPI(
    title="QuickOJ API",
    description="QuickOJ — 算法竞赛在线评测平台 RESTful API",
    version="1.0.0",
    lifespan=lifespan,
)

# ---- CORS 中间件 ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- 静态文件挂载 ----
# 题面图片: /images/problems/{problem_id}/xxx.png → data/images/problems/{problem_id}/xxx.png
if IMAGES_DIR.exists():
    app.mount("/images/problems", StaticFiles(directory=str(IMAGES_DIR)), name="problem_images")

# 用户头像: /avatars/xxx → data/avatars/xxx
if AVATARS_DIR.exists():
    app.mount("/avatars", StaticFiles(directory=str(AVATARS_DIR)), name="avatars")


# ---- 注册路由 ----
from app.routers import user, admin, problems, submissions, tags, notifications, ranking

app.include_router(user.router, prefix="/user", tags=["用户"])
app.include_router(admin.router, prefix="/admin", tags=["管理"])
app.include_router(problems.router, prefix="/problems", tags=["题目"])
app.include_router(submissions.router, prefix="/submissions", tags=["提交"])
app.include_router(tags.router, prefix="/tags", tags=["标签"])
app.include_router(notifications.router, prefix="/notifications", tags=["通知"])
app.include_router(ranking.router, prefix="/ranking", tags=["排行榜"])


@app.get("/")
def root():
    return {"message": "QuickOJ API", "version": "1.0.0"}
