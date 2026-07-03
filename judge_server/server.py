"""
评测机 HTTP 服务 —— 纯计算服务，不依赖后端代码，不访问数据库和文件系统。
- 主进程：接收任务（含代码+测试数据）、分配工作进程、返回结果
- 工作进程：编译代码 + 运行测试样例
"""
import os
import re
import sys
import shutil
import subprocess
import tempfile
import threading
import time
import json as _json
import uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

app = FastAPI(title="Judge Server")

MAX_WORKERS = max(1, (os.cpu_count() or 2) - 1)

_jobs: dict[str, dict] = {}
_job_semaphore = threading.Semaphore(MAX_WORKERS)


# ---------------------------------------------------------------------------
# 跨平台内存监控（内联，零外部依赖）
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes, byref, sizeof, windll, c_size_t

    _kernel32 = windll.kernel32
    _psapi = windll.psapi

    class _PMC_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", c_size_t), ("WorkingSetSize", c_size_t),
            ("QuotaPeakPagedPoolUsage", c_size_t), ("QuotaPagedPoolUsage", c_size_t),
            ("QuotaPeakNonPagedPoolUsage", c_size_t), ("QuotaNonPagedPoolUsage", c_size_t),
            ("PagefileUsage", c_size_t), ("PeakPagefileUsage", c_size_t),
            ("PrivateUsage", c_size_t),
        ]

    def _get_memory_kb(handle) -> int:
        pmc = _PMC_EX(); pmc.cb = sizeof(pmc)
        if _psapi.GetProcessMemoryInfo(wintypes.HANDLE(handle), byref(pmc), sizeof(pmc)):
            return int(pmc.PrivateUsage // 1024)
        return 0

    def _get_peak_kb(handle) -> int:
        pmc = _PMC_EX(); pmc.cb = sizeof(pmc)
        if _psapi.GetProcessMemoryInfo(wintypes.HANDLE(handle), byref(pmc), sizeof(pmc)):
            return int(pmc.PeakWorkingSetSize // 1024)
        return 0

else:
    def _get_memory_kb(pid: int) -> int:
        try:
            with open(f"/proc/{pid}/statm", "r") as f:
                parts = f.read().split()
                return int(parts[1]) * 4 if len(parts) >= 2 else 0
        except Exception: return 0

    def _get_peak_kb(pid: int) -> int:
        return _get_memory_kb(pid)


# ---------------------------------------------------------------------------
# 测试样例发现（内联）
# ---------------------------------------------------------------------------

_TEST_PATTERNS = [
    (re.compile(r"^(\d+)\.in$"),  "in"), (re.compile(r"^(\d+)\.out$"), "out"),
    (re.compile(r"^(\d+)\.ans$"), "out"),
    (re.compile(r"^input(\d+)\.txt$", re.I), "in"), (re.compile(r"^output(\d+)\.txt$", re.I), "out"),
    (re.compile(r"^answer(\d+)\.txt$", re.I), "out"),
    (re.compile(r"^in(\d+)\.txt$", re.I), "in"), (re.compile(r"^out(\d+)\.txt$", re.I), "out"),
    (re.compile(r"^ans(\d+)\.txt$", re.I), "out"),
    (re.compile(r"^test(\d+)\.in$", re.I), "in"), (re.compile(r"^test(\d+)\.out$", re.I), "out"),
    (re.compile(r"^(.+?)\.in$"), "in"), (re.compile(r"^(.+?)\.out$"), "out"),
    (re.compile(r"^(.+?)\.ans$"), "out"),
]


def _discover_test_cases(test_dir: str) -> list[tuple[str, str, str]]:
    if not os.path.isdir(test_dir): return []
    inputs, answers = {}, {}
    for fname in os.listdir(test_dir):
        full = os.path.join(test_dir, fname)
        if not os.path.isfile(full): continue
        for pat, ftype in _TEST_PATTERNS:
            m = pat.match(fname)
            if m:
                (inputs if ftype == "in" else answers)[m.group(1)] = full
                break
    pairs = []
    for tid in sorted(inputs, key=lambda x: int(x) if x.isdigit() else x):
        if tid in answers:
            pairs.append((tid, inputs[tid], answers[tid]))
    # 输出题：仅有答案文件时生成空输入
    empty = None
    for tid in sorted(answers, key=lambda x: int(x) if x.isdigit() else x):
        if tid not in inputs:
            if empty is None:
                empty = os.path.join(test_dir, "_empty.in")
                with open(empty, "w") as f: f.write("")
            pairs.append((tid, empty, answers[tid]))
    seen = set(); ordered = []
    for p in pairs:
        if p[0] not in seen: seen.add(p[0]); ordered.append(p)
    ordered.sort(key=lambda x: int(x[0]) if x[0].isdigit() else x[0])
    return ordered


# ---------------------------------------------------------------------------
# 单次运行比对（内联）
# ---------------------------------------------------------------------------

def _run_single_test(exe_or_src: str, input_path: str, answer_path: str,
                     time_limit_s: float, memory_mb: float | None, language: str) -> dict:
    result: dict = {"status": "Unknown", "message": "", "program_output": "",
                    "time_used": None, "memory_used_kb": 0}
    if not os.path.isfile(exe_or_src) or not os.path.isfile(input_path):
        result["status"] = "System Error"
        result["message"] = "文件不存在"; return result

    cmd = [sys.executable, exe_or_src] if language == "python3" else [exe_or_src]
    mem_limit_bytes = int(memory_mb * 1024 * 1024) if memory_mb else None
    peak_kb = 0; killed = threading.Event()
    # 子进程工作目录限制在临时目录，阻止访问评测机文件系统
    run_cwd = os.path.dirname(os.path.abspath(exe_or_src))

    try:
        f_in = open(input_path, "r", newline="")
        proc = subprocess.Popen(cmd, stdin=f_in, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, cwd=run_cwd)

        def monitor():
            nonlocal peak_kb
            try:
                while proc.poll() is None and not killed.is_set():
                    if sys.platform == "win32": cur = _get_memory_kb(int(proc._handle))
                    else: cur = _get_memory_kb(proc.pid)
                    if cur > peak_kb: peak_kb = cur
                    if mem_limit_bytes and cur > mem_limit_bytes // 1024:
                        proc.kill(); killed.set(); return
                    time.sleep(0.1)
            except Exception: pass

        mon = threading.Thread(target=monitor, daemon=True)
        out_chunks, err_chunks = [], []

        def _read(stream, sink):
            try:
                for line in iter(stream.readline, ""): sink.append(line)
            except Exception: pass

        t1 = threading.Thread(target=_read, args=(proc.stdout, out_chunks), daemon=True)
        t2 = threading.Thread(target=_read, args=(proc.stderr, err_chunks), daemon=True)
        t1.start(); t2.start()

        t0 = time.perf_counter(); mon.start()
        try: proc.wait(timeout=time_limit_s)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(timeout=1); mon.join(timeout=1)
            result["status"] = "Time Limit Exceeded"
            result["message"] = f"超时 ({time_limit_s}s)"
            result["time_used"] = time_limit_s; result["memory_used_kb"] = peak_kb
            return result
        # 进程结束后立即计时，避免线程 join 开销污染
        elapsed = time.perf_counter() - t0

        t1.join(timeout=2); t2.join(timeout=2); mon.join(timeout=1)
        result["time_used"] = round(elapsed, 6)
        result["memory_used_kb"] = max(peak_kb,
            _get_peak_kb(int(proc._handle)) if sys.platform == "win32" else _get_memory_kb(proc.pid))
        result["program_output"] = "".join(out_chunks)
        stderr_text = "".join(err_chunks)

        if killed.is_set():
            result["status"] = "Memory Limit Exceeded"
            result["message"] = f"内存超限 ({memory_mb}MB)"; return result
        if proc.returncode != 0:
            result["status"] = "Runtime Error"
            msg = f"退出码 {proc.returncode}"
            if stderr_text.strip(): msg += f"\n{stderr_text.strip()}"
            result["message"] = msg; return result

        if not os.path.isfile(answer_path):
            result["status"] = "System Error"
            result["message"] = "答案文件不存在"; return result

        with open(answer_path, "r") as f: expected = f.read().rstrip("\n")
        actual = result["program_output"].rstrip("\n")

        def normalize(s: str) -> str:
            lines = [l.rstrip() for l in s.splitlines()]
            while lines and not lines[-1]: lines.pop()
            return "\n".join(lines)

        na = normalize(actual); ne = normalize(expected)
        if na == ne:
            result["status"] = "Accepted"; result["message"] = "答案正确"
        elif na.split() == ne.split():
            result["status"] = "Presentation Error"
            result["message"] = "格式错误"
        else:
            result["status"] = "Wrong Answer"
            result["message"] = "答案不一致"
        return result
    except Exception as e:
        result["status"] = "System Error"; result["message"] = str(e); return result
    finally:
        try: f_in.close()
        except Exception: pass


# ---------------------------------------------------------------------------
# 编译（内联）
# ---------------------------------------------------------------------------

def _compile_cpp(code: str, work_dir: str) -> tuple[bool, str, str | None]:
    gxx = shutil.which("g++")
    if not gxx: return False, "g++ not found", None
    exe = os.path.join(work_dir, "main.exe")
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(gxx) + os.pathsep + env.get("PATH", "")
    cp = subprocess.run([gxx, "-O2", "-std=c++17", "-static", "-pipe", "-x", "c++", "-"],
        input=code.encode("utf-8"), capture_output=True, timeout=15, cwd=work_dir, env=env)
    if cp.returncode != 0:
        err = (cp.stderr + cp.stdout).decode("utf-8", errors="replace").strip() or f"g++ rc={cp.returncode}"
        if len(err) > 2000: err = err[:2000] + "..."
        return False, err, None
    a_exe = os.path.join(work_dir, "a.exe")
    if os.path.exists(a_exe): os.rename(a_exe, exe)
    return True, "", exe


# ---------------------------------------------------------------------------
# 工作进程入口
# ---------------------------------------------------------------------------

PY_SANDBOX_PREAMBLE = r'''
import builtins as __bx__
_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "ascii": ascii, "bin": bin,
    "bool": bool, "bytearray": bytearray, "bytes": bytes, "callable": callable,
    "chr": chr, "complex": complex, "dict": dict, "dir": dir, "divmod": divmod,
    "enumerate": enumerate, "filter": filter, "float": float, "format": format,
    "frozenset": frozenset, "getattr": getattr, "hasattr": hasattr, "hash": hash,
    "hex": hex, "id": id, "input": input, "int": int, "isinstance": isinstance,
    "issubclass": issubclass, "iter": iter, "len": len, "list": list, "map": map,
    "max": max, "memoryview": memoryview, "min": min, "next": next, "object": object,
    "oct": oct, "ord": ord, "pow": pow, "print": print, "property": property,
    "range": range, "repr": repr, "reversed": reversed, "round": round,
    "set": set, "setattr": setattr, "slice": slice, "sorted": sorted,
    "staticmethod": staticmethod, "str": str, "sum": sum, "super": super,
    "tuple": tuple, "type": type, "vars": vars, "zip": zip,
    "Exception": Exception, "StopIteration": StopIteration, "ValueError": ValueError,
    "TypeError": TypeError, "KeyError": KeyError, "IndexError": IndexError,
    "ZeroDivisionError": ZeroDivisionError, "OverflowError": OverflowError,
    "ArithmeticError": ArithmeticError, "AssertionError": AssertionError,
    "EOFError": EOFError, "ImportError": ImportError, "OSError": OSError,
    "RuntimeError": RuntimeError, "MemoryError": MemoryError, "RecursionError": RecursionError,
    "True": True, "False": False, "None": None, "Ellipsis": Ellipsis,
}
for _k, _v in _SAFE_BUILTINS.items():
    __bx__.__dict__[_k] = _v

_ORIG_IMPORT = __import__
def _safe_import(name, *args, **kwargs):
    _BLOCKED = ("os", "sys", "subprocess", "socket", "shutil", "ctypes",
                "multiprocessing", "threading", "signal", "atexit", "code",
                "codeop", "compileall", "imp", "importlib", "pkgutil",
                "runpy", "tokenize", "py_compile", "_thread", "concurrent")
    if name in _BLOCKED or name.startswith("_"):
        raise ImportError(f"Module '{name}' is not allowed")
    return _ORIG_IMPORT(name, *args, **kwargs)
__bx__.__import__ = _safe_import

__bx__.open = None
__bx__.exec = None
__bx__.eval = None
__bx__.compile = None
__bx__.__import__ = _safe_import
del __bx__, _ORIG_IMPORT, _SAFE_BUILTINS, _k, _v
'''


def _worker_job(job_id: str, job: dict, test_files: list[tuple[str, bytes]]):
    work_dir = tempfile.mkdtemp(prefix="js_worker_")
    try:
        code = job["code"]
        language = job["language"]
        time_limit_s = job["time_limit_ms"] / 1000.0
        memory_mb = job["memory_limit_kb"] / 1024.0

        ext = ".cpp" if language == "cpp" else ".py"
        src_path = os.path.join(work_dir, f"main{ext}")

        if language == "python3":
            code = PY_SANDBOX_PREAMBLE + "\n" + code

        with open(src_path, "w", encoding="utf-8") as f: f.write(code)

        # 写入测试数据文件（编译前完成，以便尽早发现测试用例）
        data_dir = os.path.join(work_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        for fname, content in test_files:
            dest = os.path.join(data_dir, fname)
            with open(dest, "wb") as df: df.write(content)

        # 正式评测前先发现测试用例，立即渲染全部测试点占位
        pairs = _discover_test_cases(data_dir)
        if not pairs:
            _jobs[job_id]["result"] = {"summary": {"status": "System Error", "total": 0, "passed": 0, "failed": 0},
                    "tests": [], "error": "测试样例为空", "run_time": 0, "run_memory": 0}
            _jobs[job_id]["status"] = "done"
            return
        initial = [{"name": n, "status": "Pending", "time_used": None, "memory_used_kb": 0} for n, _, _ in pairs]
        _jobs[job_id]["result"] = {
            "summary": {"status": "Running", "total": len(pairs), "passed": 0, "failed": 0},
            "tests": initial, "run_time": 0, "run_memory": 0,
        }

        compiled_exe = None
        if language == "cpp":
            ok, err, compiled_exe = _compile_cpp(code, work_dir)
            if not ok:
                _jobs[job_id]["result"] = {"summary": {"status": "Compile Error", "total": 0, "passed": 0, "failed": 0},
                        "tests": [], "compile": {"status": "Compile Error", "output": err},
                        "run_time": 0, "run_memory": 0}
                _jobs[job_id]["status"] = "done"
                return

        exe_or_src = compiled_exe if compiled_exe else src_path
        if job.get("is_debug"):
            in_path = os.path.join(work_dir, "input.txt")
            ans_path = os.path.join(work_dir, "answer.txt")
            with open(in_path, "w", encoding="utf-8", newline="") as f:
                f.write(job.get("debug_input", ""))
            with open(ans_path, "w", encoding="utf-8", newline="") as f:
                f.write("")
            r = _run_single_test(exe_or_src, in_path, ans_path, time_limit_s, memory_mb, language)
            r["name"] = "debug"
            if r["status"] in ("Accepted", "Wrong Answer", "Presentation Error"):
                r["status"] = "Accepted"
            _jobs[job_id]["result"] = {"summary": {"status": r["status"], "total": 1,
                                "passed": 1 if r["status"] == "Accepted" else 0,
                                "failed": 0 if r["status"] == "Accepted" else 1},
                    "tests": [r],
                    "run_time": int((r.get("time_used") or 0) * 1000),
                    "run_memory": r.get("memory_used_kb", 0)}
            _jobs[job_id]["status"] = "done"
            return

        # 正式评测：逐个运行测试点，每完成一个更新对应位置
        all_tests = list(initial)  # 全部 N 个占位，逐一替换为真实结果
        passed = 0
        for idx, (name, in_path, ans_path) in enumerate(pairs):
            r = _run_single_test(exe_or_src, in_path, ans_path, time_limit_s, memory_mb, language)
            r["name"] = name
            all_tests[idx] = r
            if r.get("status") == "Accepted": passed += 1
            done = idx + 1
            run_times = [t.get("time_used") or 0 for t in all_tests[:done]]
            run_mems = [t.get("memory_used_kb") or 0 for t in all_tests[:done]]
            # 中间结果：去掉 output/message 减轻传输负担，仅保留状态/时间/内存
            slim = [{k: v for k, v in t.items() if k not in ("program_output", "message")} for t in all_tests]
            _jobs[job_id]["result"] = {
                "summary": {"status": "Running", "total": len(pairs), "passed": passed, "failed": done - passed},
                "tests": slim,
                "run_time": int(max(run_times) * 1000) if run_times else 0,
                "run_memory": int(max(run_mems)) if run_mems else 0,
            }

        overall = "Accepted" if passed == len(all_tests) else (
            next((r["status"] for r in all_tests if r["status"] != "Accepted"), "System Error"))
        result = {"summary": {"status": overall, "total": len(all_tests), "passed": passed, "failed": len(all_tests) - passed},
                  "tests": all_tests}
        if all_tests:
            result["run_time"] = int(max((t.get("time_used") or 0 for t in all_tests)) * 1000)
            result["run_memory"] = int(max((t.get("memory_used_kb") or 0 for t in all_tests)))
        _jobs[job_id]["result"] = result
        _jobs[job_id]["status"] = "done"
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "workers": MAX_WORKERS}


@app.get("/status")
def status():
    running = sum(1 for j in _jobs.values() if j["status"] == "running")
    queued = sum(1 for j in _jobs.values() if j["status"] == "queued")
    return {"running": running, "queued": queued, "total_jobs": len(_jobs), "workers": MAX_WORKERS}


@app.get("/job/{job_id}")
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if not job: return JSONResponse({"status": "not_found"}, status_code=404)
    return {"status": job["status"], "result": job.get("result")}


@app.post("/judge")
async def do_judge(
    code: str = Form(...),
    language: str = Form(...),
    problem_id: int = Form(...),
    problem_type: str = Form("traditional"),
    time_limit_ms: int = Form(1000),
    memory_limit_kb: int = Form(256000),
    is_test_run: bool = Form(False),
    is_debug: bool = Form(False),
    debug_input: str = Form(""),
    test_data: list[UploadFile] = File([]),
):
    job_id = uuid.uuid4().hex[:12]
    job = {
        "code": code, "language": language, "problem_id": problem_id,
        "time_limit_ms": time_limit_ms, "memory_limit_kb": memory_limit_kb,
        "is_test_run": is_test_run, "is_debug": is_debug,
        "debug_input": debug_input,
    }
    # 读取上传的测试数据文件
    test_files = [(f.filename or "unknown", await f.read()) for f in test_data]

    _jobs[job_id] = {"status": "queued", "result": None, "created_at": time.time()}

    def _run():
        _job_semaphore.acquire()
        try:
            try:
                _worker_job(job_id, job, test_files)
            except Exception as e:
                _jobs[job_id]["result"] = {"summary": {"status": "System Error", "total": 0, "passed": 0, "failed": 0},
                                           "tests": [], "error": str(e), "run_time": 0, "run_memory": 0}
                _jobs[job_id]["status"] = "done"
        finally:
            _job_semaphore.release()

    _jobs[job_id]["status"] = "running"
    threading.Thread(target=_run, daemon=True).start()
    return {"job_id": job_id, "status": "queued"}


import asyncio as _asyncio

async def _cleanup_loop():
    while True:
        await _asyncio.sleep(60)
        now = time.time()
        stale = [jid for jid, j in _jobs.items() if j["status"] == "done" and now - j["created_at"] > 300]
        for jid in stale: del _jobs[jid]


@app.on_event("startup")
async def startup():
    _asyncio.create_task(_cleanup_loop())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
