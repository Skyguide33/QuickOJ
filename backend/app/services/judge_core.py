"""
评测核心 —— 编译、运行、比对。
使用 subprocess.Popen + 后台内存监控，提供精确的运行时间和峰值内存。
"""
import os
import re
import sys
import shutil
import subprocess
import tempfile
import threading
import time

# ---------------------------------------------------------------------------
# 跨平台内存监控
# ---------------------------------------------------------------------------

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes, byref, sizeof, windll, c_size_t

    _kernel32 = windll.kernel32
    _psapi = windll.psapi

    # 抑制 Windows 错误报告弹窗（崩溃时不弹对话框，直接退出）
    # SEM_FAILCRITICALERRORS(1) | SEM_NOGPFAULTERRORBOX(2) | SEM_NOOPENFILEERRORBOX(0x8000) = 0x8003
    _kernel32.SetErrorMode(_kernel32.SetErrorMode(0) | 0x8003)

    class _PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb",                         wintypes.DWORD),
            ("PageFaultCount",             wintypes.DWORD),
            ("PeakWorkingSetSize",         c_size_t),
            ("WorkingSetSize",             c_size_t),
            ("QuotaPeakPagedPoolUsage",    c_size_t),
            ("QuotaPagedPoolUsage",        c_size_t),
            ("QuotaPeakNonPagedPoolUsage", c_size_t),
            ("QuotaNonPagedPoolUsage",     c_size_t),
            ("PagefileUsage",              c_size_t),
            ("PeakPagefileUsage",          c_size_t),
            ("PrivateUsage",               c_size_t),
        ]

    def _get_memory_kb(proc_handle) -> int:
        """获取进程当前 PrivateUsage (KB)"""
        pmc = _PROCESS_MEMORY_COUNTERS_EX()
        pmc.cb = sizeof(pmc)
        if _psapi.GetProcessMemoryInfo(
            wintypes.HANDLE(proc_handle), byref(pmc), sizeof(pmc),
        ):
            return int(pmc.PrivateUsage // 1024)
        return 0

    def _get_peak_memory_kb(proc_handle) -> int:
        """获取进程峰值 WorkingSetSize (KB)"""
        pmc = _PROCESS_MEMORY_COUNTERS_EX()
        pmc.cb = sizeof(pmc)
        if _psapi.GetProcessMemoryInfo(
            wintypes.HANDLE(proc_handle), byref(pmc), sizeof(pmc),
        ):
            return int(pmc.PeakWorkingSetSize // 1024)
        return 0

else:
    def _get_memory_kb(pid: int) -> int:
        try:
            with open(f"/proc/{pid}/statm", "r") as f:
                parts = f.read().split()
                if len(parts) >= 2:
                    return int(parts[1]) * 4  # resident set size in pages → KB
        except Exception:
            pass
        return 0

    def _get_peak_memory_kb(pid: int) -> int:
        return _get_memory_kb(pid)  # Linux 没有简单的 peak 接口，用当前值近似


# ---------------------------------------------------------------------------
# 测试样例发现
# ---------------------------------------------------------------------------

_TEST_PATTERNS = [
    # 数字格式先匹配
    (re.compile(r"^(\d+)\.in$"),  "in"),
    (re.compile(r"^(\d+)\.out$"), "out"),
    (re.compile(r"^(\d+)\.ans$"), "out"),
    (re.compile(r"^input(\d+)\.txt$",  re.I), "in"),
    (re.compile(r"^output(\d+)\.txt$", re.I), "out"),
    (re.compile(r"^answer(\d+)\.txt$", re.I), "out"),
    (re.compile(r"^in(\d+)\.txt$",  re.I), "in"),
    (re.compile(r"^out(\d+)\.txt$", re.I), "out"),
    (re.compile(r"^ans(\d+)\.txt$", re.I), "out"),
    (re.compile(r"^test(\d+)\.in$",  re.I), "in"),
    (re.compile(r"^test(\d+)\.out$", re.I), "out"),
    # 通用：任意文件名.in/.out/.ans（放在最后作为兜底）
    (re.compile(r"^(.+?)\.in$"),  "in"),
    (re.compile(r"^(.+?)\.out$"), "out"),
    (re.compile(r"^(.+?)\.ans$"), "out"),
]


def discover_test_cases(test_dir: str) -> list[tuple[str, str, str]]:
    """
    扫描目录，返回按 test_id 排序的 (name, input_path, answer_path) 列表。
    - 传统题：配对 .in / .out
    - 输出题：仅有 .out 时自动生成空输入
    """
    if not os.path.isdir(test_dir):
        return []

    inputs = {}
    answers = {}
    for fname in os.listdir(test_dir):
        full = os.path.join(test_dir, fname)
        if not os.path.isfile(full):
            continue
        tid, ftype = _classify(fname)
        if tid is None:
            continue
        (inputs if ftype == "in" else answers)[tid] = full

    pairs = []
    for tid in sorted(inputs, key=_sort_key):
        if tid in answers:
            pairs.append((tid, inputs[tid], answers[tid]))

    # 输出题：仅答案文件，生成空输入
    empty = None
    for tid in sorted(answers, key=_sort_key):
        if tid not in inputs:
            if empty is None:
                empty = os.path.join(test_dir, "_empty.in")
                with open(empty, "w", encoding="utf-8") as f:
                    f.write("")
            pairs.append((tid, empty, answers[tid]))

    # 去重排序
    seen = set()
    ordered = []
    for p in pairs:
        if p[0] not in seen:
            seen.add(p[0]); ordered.append(p)
    ordered.sort(key=lambda x: _sort_key(x[0]))
    return ordered


def _classify(filename: str) -> tuple[str | None, str | None]:
    for pat, ftype in _TEST_PATTERNS:
        m = pat.match(filename)
        if m:
            return m.group(1), ftype
    return None, None


def _sort_key(tid: str):
    return int(tid) if tid.isdigit() else tid


# ---------------------------------------------------------------------------
# C++ 编译
# ---------------------------------------------------------------------------

def compile_cpp(src: str, out_exe: str, gxx: str | None = None) -> tuple[bool, str]:
    """编译 C++ 源码，返回 (成功, 错误信息)"""
    if gxx is None:
        gxx = shutil.which("g++")
    if not gxx or not os.path.isfile(src):
        return False, "源文件或 g++ 不可用"

    cmd = [gxx, "-O2", "-std=c++17", "-static", src, "-o", out_exe]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
        if proc.returncode != 0:
            err = (proc.stderr + proc.stdout).strip()
            return False, err or f"g++ 返回码 {proc.returncode}"
        return True, ""
    except FileNotFoundError:
        return False, "未找到 g++"
    except subprocess.TimeoutExpired:
        return False, "编译超时 (30s)"
    except Exception as e:
        return False, f"编译异常: {e}"


# ---------------------------------------------------------------------------
# 单次运行 + 比对
# ---------------------------------------------------------------------------

def run_single_test(
    exe_or_src: str,
    input_path: str,
    answer_path: str,
    time_limit_s: float,
    memory_mb: float | None,
    language: str,
) -> dict:
    """
    子进程运行 + 后台内存监控，返回:
        { name, status, message, program_output, time_used, memory_used_kb }
    time_used 单位秒，memory_used_kb 单位 KB。
    """
    result: dict = {
        "status": "Unknown", "message": "", "program_output": "",
        "time_used": None, "memory_used_kb": 0,
    }

    if not os.path.isfile(exe_or_src) or not os.path.isfile(input_path):
        result["status"] = "System Error"
        result["message"] = "可执行文件或输入文件不存在"
        return result

    cmd = [sys.executable, exe_or_src] if language == "python3" else [exe_or_src]
    mem_limit_bytes = int(memory_mb * 1024 * 1024) if memory_mb else None
    peak_mem_kb = 0
    killed_by_mem = threading.Event()

    try:
        f_in = open(input_path, "r", newline="")
        proc = subprocess.Popen(
            cmd, stdin=f_in,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )

        # ---- 后台内存监控线程 ----
        def monitor():
            nonlocal peak_mem_kb
            try:
                while proc.poll() is None and not killed_by_mem.is_set():
                    if sys.platform == "win32":
                        cur = _get_memory_kb(int(proc._handle))
                    else:
                        cur = _get_memory_kb(proc.pid)
                    if cur > peak_mem_kb:
                        peak_mem_kb = cur
                    if mem_limit_bytes and cur > mem_limit_bytes // 1024:
                        proc.kill()
                        killed_by_mem.set()
                        return
                    time.sleep(0.1)
            except Exception:
                pass

        mon = threading.Thread(target=monitor, daemon=True)

        # ---- 用独立线程读 stdout/stderr ----
        stdout_chunks = []
        stderr_chunks = []

        def _read(stream, sink):
            try:
                for line in iter(stream.readline, ""):
                    sink.append(line)
            except Exception:
                pass

        t_stdout = threading.Thread(target=_read, args=(proc.stdout, stdout_chunks), daemon=True)
        t_stderr = threading.Thread(target=_read, args=(proc.stderr, stderr_chunks), daemon=True)
        t_stdout.start()
        t_stderr.start()

        # ---- 计时 + 等待进程退出 ----
        t0 = time.perf_counter()
        mon.start()
        try:
            proc.wait(timeout=time_limit_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=1)
            mon.join(timeout=1)
            result["status"] = "Time Limit Exceeded"
            result["message"] = f"超过时间限制 ({time_limit_s}s)"
            result["time_used"] = time_limit_s
            result["memory_used_kb"] = peak_mem_kb
            return result

        # 等待读取线程收尾
        t_stdout.join(timeout=2)
        t_stderr.join(timeout=2)
        mon.join(timeout=1)

        stdout_data = "".join(stdout_chunks)
        stderr_data = "".join(stderr_chunks)

        elapsed = time.perf_counter() - t0

        # 最终采样一次峰值
        if sys.platform == "win32":
            peak_mem_kb = max(peak_mem_kb, _get_peak_memory_kb(int(proc._handle)))
        else:
            peak_mem_kb = max(peak_mem_kb, _get_memory_kb(proc.pid))

        result["time_used"] = round(elapsed, 6)
        result["memory_used_kb"] = peak_mem_kb
        result["program_output"] = stdout_data or ""

        # ---- 判断退出原因 ----
        if killed_by_mem.is_set():
            result["status"] = "Memory Limit Exceeded"
            result["message"] = f"内存超限 ({memory_mb} MB)"
            return result

        if proc.returncode != 0:
            result["status"] = "Runtime Error"
            msg = f"退出码 {proc.returncode}"
            if stderr_data and stderr_data.strip():
                msg += f"\n{stderr_data.strip()}"
            result["message"] = msg
            return result

        # ---- 比对输出（专业 OJ 标准：去行尾空格、去末尾空行、区分 PE/WA） ----
        if not os.path.isfile(answer_path):
            result["status"] = "System Error"
            result["message"] = "答案文件不存在"
            return result

        with open(answer_path, "r") as f:
            expected = f.read()
        actual = result["program_output"]

        def normalize(s: str) -> str:
            """去行尾空格 + 去末尾空行"""
            lines = [line.rstrip() for line in s.splitlines()]
            while lines and not lines[-1]:
                lines.pop()
            return "\n".join(lines)

        norm_actual = normalize(actual)
        norm_expected = normalize(expected)

        if norm_actual == norm_expected:
            result["status"] = "Accepted"
            result["message"] = "答案正确"
            return result

        # 严格比对不通过 → 判断是 PE 还是 WA
        def tokens(s: str) -> list[str]:
            """提取所有非空白 token"""
            return s.split()

        if tokens(norm_actual) == tokens(norm_expected):
            result["status"] = "Presentation Error"
            result["message"] = "输出内容正确，但格式错误（空格/换行与答案不一致）"
        else:
            result["status"] = "Wrong Answer"
            result["message"] = "输出内容与答案不一致"
        return result

    except Exception as e:
        result["status"] = "System Error"
        result["message"] = str(e)
        return result
    finally:
        try:
            f_in.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 批量评测（由调度器并发调用每个测试样例）
# ---------------------------------------------------------------------------

def discover_and_prepare(
    test_dir: str,
    source_path: str,
    language: str,
    time_limit_s: float,
    memory_mb: float | None,
    output_exe: str | None = None,
) -> tuple[list[dict], dict | None]:
    """
    准备工作：发现测试样例 + C++ 编译。
    返回 (测试样例对列表, 编译信息 dict)。
    编译失败则测试样例对列表为空，编译信息含错误。
    """
    pairs = discover_test_cases(test_dir)
    if not pairs:
        return [], {"status": "System Error", "output": f"目录 {test_dir} 中未发现测试样例"}

    compile_info = None
    if language == "cpp":
        if output_exe and os.path.isfile(output_exe):
            compile_info = {"status": "OK", "output": ""}
        else:
            # 需要自行编译
            base = os.path.splitext(source_path)[0]
            output_exe = base + (".exe" if sys.platform == "win32" else "")
            ok, err = compile_cpp(source_path, output_exe)
            compile_info = {"status": "OK" if ok else "Compile Error",
                            "output": err if not ok else ""}
            if not ok:
                return [], compile_info

    return pairs, compile_info


def run_one_test(pair: tuple[str, str, str], exe_or_src: str,
                 time_limit_s: float, memory_mb: float | None,
                 language: str) -> dict:
    """对一组样例执行单次评测（供并发调度调用）"""
    name, input_path, answer_path = pair
    res = run_single_test(exe_or_src, input_path, answer_path,
                          time_limit_s, memory_mb, language)
    res["name"] = name
    return res