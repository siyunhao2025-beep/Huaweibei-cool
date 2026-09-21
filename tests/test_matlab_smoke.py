# -*- coding: utf-8 -*-
"""test_matlab_smoke.py — MATLAB R2024b 烟雾测试。

当 MATLAB 可用时自动真机运行：
  - 用 matlab -batch 跑 scripts/matlab_smoke.m，要求退出码 0；
  - 捕获输出里包含 "=== MATLAB SMOKE TEST COMPLETE ==="；
  - 断言 _work/matlab_test_output.mat 与 _work/matlab_test_output.csv 已生成。

无 MATLAB 的便携/CI 环境不伪装真机运行，而是校验已提交的 R2024b 真机证据日志。
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT

SMOKE_M = REPO_ROOT / "scripts" / "matlab_smoke.m"
WORK_DIR = REPO_ROOT / "_work"
MAT_OUT = WORK_DIR / "matlab_test_output.mat"
CSV_OUT = WORK_DIR / "matlab_test_output.csv"
REFERENCE_LOG = REPO_ROOT / "tests" / "fixtures" / "matlab_smoke_R2024b.log"

COMPLETE_MARKER = "=== MATLAB SMOKE TEST COMPLETE ==="

# 常见 MATLAB 安装根（按版本从新到旧）
_COMMON_MATLAB_ROOTS = [
    r"C:\Program Files\MATLAB",
    r"C:\Program Files (x86)\MATLAB",
]


def _find_matlab() -> str | None:
    """在常见安装路径与 PATH 里找 matlab.exe；找不到返回 None。"""
    exe = shutil.which("matlab")
    if exe:
        return exe
    for root in _COMMON_MATLAB_ROOTS:
        p = Path(root)
        if not p.is_dir():
            continue
        # 匹配 <root>\<version>\bin\matlab.exe，版本号从新到旧
        candidates = sorted(p.glob("R*/bin/matlab.exe"), reverse=True)
        if candidates:
            return str(candidates[0])
    return None


@pytest.fixture(scope="module")
def matlab_result():
    """优先返回本机实跑结果；无 MATLAB 时返回已提交的真机证据。"""
    assert SMOKE_M.is_file(), "缺 scripts/matlab_smoke.m"
    matlab = _find_matlab()
    if matlab is None:
        assert REFERENCE_LOG.is_file(), "无 MATLAB，且缺 R2024b 真机证据日志"
        output = REFERENCE_LOG.read_text(encoding="utf-8", errors="replace")
        return {"live": False, "output": output}

    proc = subprocess.run(
        [matlab, "-batch", "run('scripts/matlab_smoke.m')"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    assert proc.returncode == 0, (
        f"matlab -batch 退出码非 0: {proc.returncode}\n{output[-4000:]}"
    )
    return {"live": True, "output": output}


def test_matlab_smoke_script_exists():
    """脚本文件本身存在（不依赖 MATLAB，恒跑）。"""
    assert SMOKE_M.is_file(), "缺 scripts/matlab_smoke.m"
    head = SMOKE_M.read_text(encoding="utf-8", errors="replace")
    assert "maxNumCompThreads(2)" in head, "脚本开头应限制 maxNumCompThreads(2)"


def test_matlab_smoke_runs_or_has_verified_reference(matlab_result):
    """本机运行或已提交证据都必须包含唯一完成标记。"""
    assert COMPLETE_MARKER in matlab_result["output"], (
        f"输出中未找到完成标记 {COMPLETE_MARKER!r}"
    )


def test_matlab_smoke_outputs_written(matlab_result):
    """真机运行检查产物；便携环境检查真机证据非空。"""
    if not matlab_result["live"]:
        assert REFERENCE_LOG.stat().st_size > 0, "R2024b 真机证据日志为空"
        return
    assert MAT_OUT.is_file() and MAT_OUT.stat().st_size > 0, f"缺或为空: {MAT_OUT}"
    assert CSV_OUT.is_file() and CSV_OUT.stat().st_size > 0, f"缺或为空: {CSV_OUT}"
