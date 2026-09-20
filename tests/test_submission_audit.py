# -*- coding: utf-8 -*-
"""test_submission_audit.py — submission_audit.py 对 example.tex 的审计烟雾测试。

example.tex 预期会检出身份标志/缺 AI 披露（这是设计内的预期 FAIL），
本测试只要求：脚本能运行、退出码为 0 或 1（而非异常崩溃）、输出可解析。
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ASSETS, REPO_ROOT, SCRIPTS

EXAMPLE = ASSETS / "paper-template" / "example.tex"


def test_submission_audit_runs_on_example():
    assert EXAMPLE.is_file(), f"缺 example.tex: {EXAMPLE}"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "submission_audit.py"),
         "--paper", str(EXAMPLE), "--json"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=60)
    # 预期会因身份标志/缺 AI 披露返回 1；关键是不抛异常、有 JSON 输出
    assert proc.returncode in (0, 1), f"退出码异常: {proc.returncode}\n{proc.stderr}"
    out = json.loads(proc.stdout)
    assert "checks" in out and "passed" in out
    # example.tex 含参赛队号等，应至少做了身份/披露这两项检查
    descs = " ".join(c["desc"] for c in out["checks"])
    assert "身份" in descs or "AI" in descs
