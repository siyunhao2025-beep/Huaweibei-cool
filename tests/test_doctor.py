# -*- coding: utf-8 -*-
"""test_doctor.py — scripts/doctor.py 环境自检（Wave5-C）。

用 --json 跑 doctor.py，断言：
  - 退出码 0（当前开发环境不应有 FAIL）；
  - JSON 含 summary / checks；
  - 九个检查项 id 齐全；
  - python_version / deps / pytest 在本机不是 FAIL（环境可用）。

不直接断言每项 PASS（CI 无 MATLAB / 无 Word / 无 graphviz 属正常，允许 WARN）。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, SCRIPTS

DOCTOR = SCRIPTS / "doctor.py"

EXPECTED_IDS = {
    "python_version",
    "deps",
    "pytest",
    "git",
    "xelatex",
    "matplotlib_cn_font",
    "matlab",
    "word_com",
    "graphviz",
}


def _run_doctor_json() -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(DOCTOR), "--json"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert proc.returncode in (0, 1), (
        f"doctor.py 异常退出码 {proc.returncode}\n{proc.stderr[-2000:]}"
    )
    data = json.loads(proc.stdout)
    return proc.returncode, data


def test_doctor_script_exists():
    assert DOCTOR.is_file(), "缺 scripts/doctor.py"


def test_doctor_help_exits_zero():
    proc = subprocess.run(
        [sys.executable, str(DOCTOR), "--help"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert proc.returncode == 0, f"--help 退出码非 0: {proc.returncode}"


def test_doctor_json_shape():
    code, data = _run_doctor_json()
    assert "summary" in data and "checks" in data
    summ = data["summary"]
    for k in ("pass", "warn", "fail", "skip", "total"):
        assert k in summ, f"summary 缺 {k}"
    ids = {c["id"] for c in data["checks"]}
    assert EXPECTED_IDS <= ids, f"缺检查项: {EXPECTED_IDS - ids}"
    # 干净 CI 环境（CI=true）没有 xelatex/MATLAB/Word，FAIL 属预期；
    # 仅在开发机上要求零 FAIL（本机已验证 8 PASS / 1 WARN）。
    if not os.environ.get("CI"):
        assert summ["fail"] == 0, f"doctor 报告 FAIL：{[c for c in data['checks'] if c['status']=='FAIL']}"
        # 退出码与 FAIL 数一致：有 FAIL 才非 0
        assert code == 0


def test_doctor_core_checks_not_fail():
    _, data = _run_doctor_json()
    by_id = {c["id"]: c for c in data["checks"]}
    # 这三项是本仓库 Python 链的硬依赖，开发机上必须可用
    for cid in ("python_version", "deps", "pytest"):
        assert by_id[cid]["status"] != "FAIL", (
            f"{cid} 报告 FAIL: {by_id[cid]['detail']}"
        )
