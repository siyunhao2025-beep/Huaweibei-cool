# -*- coding: utf-8 -*-
"""test_matlab_smoke.py — MATLAB R2024b 真机烟雾测试（opt-in）。

默认 SKIP：
  - 找不到 matlab.exe（常见安装路径 + PATH 探测），或
  - 未设置环境变量 HUAWEI_RUN_MATLAB=1
则自动 skip，不在 CI / 无 MATLAB 机器上失败。

当 MATLAB 可用且 HUAWEI_RUN_MATLAB=1 时：
  - 用 matlab -batch 跑 scripts/matlab_smoke.m，要求退出码 0；
  - 捕获输出里包含 "=== MATLAB SMOKE TEST COMPLETE ==="；
  - 断言 _work/matlab_test_output.mat 与 _work/matlab_test_output.csv 已生成。

证据日志（人工留痕）：tests/fixtures/matlab_smoke_R2024b.log。
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT

SMOKE_M = REPO_ROOT / "scripts" / "matlab_smoke.m"
WORK_DIR = REPO_ROOT / "_work"
MAT_OUT = WORK_DIR / "matlab_test_output.mat"
CSV_OUT = WORK_DIR / "matlab_test_output.csv"

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


def _matlab_enabled() -> bool:
    return os.environ.get("HUAWEI_RUN_MATLAB", "") == "1"


def _require_matlab_or_skip():
    if not SMOKE_M.is_file():
        pytest.skip("scripts/matlab_smoke.m 不存在")
    matlab = _find_matlab()
    if matlab is None:
        pytest.skip("MATLAB not available (未在常见路径/PATH 找到 matlab.exe)")
    if not _matlab_enabled():
        pytest.skip("HUAWEI_RUN_MATLAB not set（默认跳过真机 MATLAB 测试）")
    return matlab


def test_matlab_smoke_script_exists():
    """脚本文件本身存在（不依赖 MATLAB，恒跑）。"""
    assert SMOKE_M.is_file(), "缺 scripts/matlab_smoke.m"
    head = SMOKE_M.read_text(encoding="utf-8", errors="replace")
    assert "maxNumCompThreads(2)" in head, "脚本开头应限制 maxNumCompThreads(2)"


def test_matlab_smoke_runs():
    """真机跑 matlab -batch；无 MATLAB / 未开环境变量则 skip。"""
    matlab = _require_matlab_or_skip()

    # 用 -batch 跑脚本；cwd 固定为仓库根，保证相对路径可解析
    cmd = [matlab, "-batch", "run('scripts/matlab_smoke.m')"]
    proc = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,  # 冷启动 + license checkout 可能较慢
    )
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")

    # 退出码必须为 0
    assert proc.returncode == 0, (
        f"matlab -batch 退出码非 0: {proc.returncode}\n"
        f"---- stdout ----\n{proc.stdout}\n---- stderr ----\n{proc.stderr}"
    )
    # 必须出现完成标记
    assert COMPLETE_MARKER in combined, (
        f"输出中未找到完成标记 {COMPLETE_MARKER!r}\n----\n{combined[-4000:]}"
    )


def test_matlab_smoke_outputs_written():
    """.mat / .csv 产物已生成（opt-in 真机跑后断言）。"""
    _require_matlab_or_skip()
    assert MAT_OUT.is_file(), f"缺 {MAT_OUT}"
    assert CSV_OUT.is_file(), f"缺 {CSV_OUT}"
    assert MAT_OUT.stat().st_size > 0, ".mat 为空"
    assert CSV_OUT.stat().st_size > 0, ".csv 为空"
