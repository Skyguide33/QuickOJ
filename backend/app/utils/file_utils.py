"""
文件上传/存储工具
"""
import os
import shutil
import uuid
import zipfile
from typing import List
from pathlib import Path
from fastapi import UploadFile

from app.config import (
    MAX_AVATAR_SIZE_MB,
    ALLOWED_AVATAR_TYPES,
    ALLOWED_IMAGE_TYPES,
    AVATARS_DIR,
    IMAGES_DIR,
    PROBLEMS_DATA_DIR,
    PROBLEMS_PENDING_DIR,
)

# 支持的题型及其 ZIP 包内文件要求
SUPPORTED_PROBLEM_TYPES = ("traditional", "output-only")


def validate_image(file: UploadFile, max_size_mb: int = MAX_AVATAR_SIZE_MB,
                   allowed_types: set = ALLOWED_AVATAR_TYPES) -> None:
    """校验图片文件类型和大小"""
    if not file.filename:
        raise ValueError("文件名为空")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_types:
        raise ValueError(f"不支持的文件格式，仅支持 {'/'.join(allowed_types)}")

    if file.size and file.size > max_size_mb * 1024 * 1024:
        raise ValueError(f"文件过大，请上传不超过 {max_size_mb}MB 的图片")


def save_avatar(file: UploadFile, user_id: int) -> str:
    """保存用户头像，每次用随机文件名避免浏览器缓存"""
    validate_image(file, MAX_AVATAR_SIZE_MB, ALLOWED_AVATAR_TYPES)
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    # 删除该用户的旧头像
    for old in AVATARS_DIR.glob(f"{user_id}_*"):
        try: old.unlink()
        except OSError: pass
    filepath = AVATARS_DIR / filename
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return f"/avatars/{filename}"


MAX_TEST_CASES = 120

def save_test_data(
    files: List[UploadFile],
    problem_id: int,
    problem_type: str,
    append: bool = False,
) -> tuple[list[str], str]:
    """
    将上传的 .in/.out 文件写入 pending 目录。

    - 传统题: 要求 .in/.out 成对（文件名除扩展名外相同），未成对的自动丢弃。
    - 输出题: 仅接受 .out 文件。
    - 文件名（不含扩展名）最长 2 个字符。
    - 最多 {MAX_TEST_CASES} 个样例点。
    - append=True 时不清空目标目录，同名文件直接覆盖。

    返回 (有效文件名列表, 目标目录路径)。
    """
    if problem_type not in SUPPORTED_PROBLEM_TYPES:
        raise ValueError(f"暂不支持题型「{problem_type}」")

    dest_dir = PROBLEMS_PENDING_DIR / str(problem_id)
    if not append:
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 现有文件列表
    existing = set(os.listdir(dest_dir)) if append else set()

    # 分类 .in / .out
    in_files: dict[str, UploadFile] = {}
    out_files: dict[str, UploadFile] = {}

    for f in files:
        if not f.filename:
            continue
        root, ext = os.path.splitext(f.filename)
        ext = ext.lower()
        if len(root) > 3 or len(root) == 0:
            continue
        if ext == ".in":
            in_files[root] = f
        elif ext in (".out", ".ans"):
            out_files[root] = f

    written = []

    if problem_type == "traditional":
        for root in sorted(in_files):
            if root in out_files:
                _write_file(in_files[root], dest_dir / f"{root}.in")
                _write_file(out_files[root], dest_dir / f"{root}.out")
                written.append(root)
        # 已经存在于目录中的也保留
        if append:
            for fname in sorted(existing):
                r, e = os.path.splitext(fname)
                if r not in written:
                    written.append(r)
    else:  # output-only
        for root in sorted(out_files):
            _write_file(out_files[root], dest_dir / f"{root}.out")
            written.append(root)
        if append:
            for fname in sorted(existing):
                r, e = os.path.splitext(fname)
                if r not in written:
                    written.append(r)

    written = written[:MAX_TEST_CASES]

    if not written:
        if problem_type == "traditional":
            raise ValueError("未检测到有效的 .in/.out 成对文件")
        else:
            raise ValueError("未检测到有效的 .out 文件")

    return written, str(dest_dir)


def remove_test_files(problem_id: int, roots: list[str]) -> None:
    """删除指定的测试样例文件"""
    dest_dir = PROBLEMS_PENDING_DIR / str(problem_id)
    for root in roots:
        for ext in (".in", ".out", ".ans"):
            p = dest_dir / f"{root}{ext}"
            if p.exists():
                p.unlink()


def _write_file(f: UploadFile, dest: Path):
    """将上传文件写入磁盘"""
    with open(dest, "wb") as dst:
        f.file.seek(0)
        shutil.copyfileobj(f.file, dst)


# ---------------------------------------------------------------------------
# 题面图片
# ---------------------------------------------------------------------------

def save_problem_images(files: List[UploadFile], problem_id: int) -> List[str]:
    """保存题面图片，返回相对路径列表"""
    dest_dir = IMAGES_DIR / str(problem_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for file in files:
        validate_image(file, max_size_mb=10, allowed_types=ALLOWED_IMAGE_TYPES)
        ext = file.filename.rsplit(".", 1)[-1].lower()
        safe_name = f"{uuid.uuid4().hex}.{ext}"
        filepath = dest_dir / safe_name
        with open(filepath, "wb") as f:
            f.write(file.file.read())
        paths.append(f"/images/problems/{problem_id}/{safe_name}")

    return paths


# ---------------------------------------------------------------------------
# 清理
# ---------------------------------------------------------------------------

def approve_test_data(problem_id: int) -> None:
    """审核通过：将 pending/{id} 移到 problems/{id}（覆盖旧数据）"""
    pending_dir = PROBLEMS_PENDING_DIR / str(problem_id)
    approved_dir = PROBLEMS_DATA_DIR / str(problem_id)
    if not pending_dir.exists():
        return
    if approved_dir.exists():
        shutil.rmtree(approved_dir)
    shutil.move(str(pending_dir), str(approved_dir))


def reject_test_data(problem_id: int, is_modify: bool = False) -> None:
    """审核拒绝：pending_modify 删除 pending/，pending_new 保留 pending/"""
    pending_dir = PROBLEMS_PENDING_DIR / str(problem_id)
    if pending_dir.exists() and is_modify:
        shutil.rmtree(pending_dir)


def copy_approved_to_pending(problem_id: int, excluded_roots: list[str] | None = None) -> str:
    """
    将 problems/{id} 下未被排除的样例复制到 pending/{id}。
    用于 approved → pending_modify 时保留旧样例。
    """
    exclude = set(excluded_roots or [])
    src_dir = PROBLEMS_DATA_DIR / str(problem_id)
    dst_dir = PROBLEMS_PENDING_DIR / str(problem_id)
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    if src_dir.exists():
        for fname in os.listdir(src_dir):
            root = os.path.splitext(fname)[0]
            if root not in exclude:
                shutil.copy2(src_dir / fname, dst_dir / fname)
    return str(dst_dir)


def has_pending_data(problem_id: int) -> bool:
    """是否有待审核的测试数据"""
    pending_dir = PROBLEMS_PENDING_DIR / str(problem_id)
    return pending_dir.exists() and any(pending_dir.iterdir())


def has_approved_data(problem_id: int) -> bool:
    """是否有已通过审核的测试数据"""
    approved_dir = PROBLEMS_DATA_DIR / str(problem_id)
    return approved_dir.exists() and any(approved_dir.iterdir())


def get_test_dir(problem_id: int, use_pending: bool = False) -> str:
    """获取题目测试数据目录：已通过或待审核"""
    if use_pending:
        return str(PROBLEMS_PENDING_DIR / str(problem_id))
    return str(PROBLEMS_DATA_DIR / str(problem_id))


def list_test_roots(problem_id: int) -> list[str]:
    """列出题目现有测试样例的 root 名称列表（去重排序）"""
    roots = set()
    for base in (PROBLEMS_DATA_DIR, PROBLEMS_PENDING_DIR):
        d = base / str(problem_id)
        if d.exists():
            for fname in os.listdir(d):
                root, ext = os.path.splitext(fname)
                if ext.lower() in (".in", ".out", ".ans"):
                    roots.add(root)
    return sorted(roots)


def delete_problem_data(problem_id: int) -> None:
    """删除题目的所有测试数据和图片目录"""
    for base in (PROBLEMS_DATA_DIR, PROBLEMS_PENDING_DIR, IMAGES_DIR):
        d = base / str(problem_id)
        if d.exists():
            shutil.rmtree(d)
