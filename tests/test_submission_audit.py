# -*- coding: utf-8 -*-
"""Smoke-test the 2026 cover-aware submission audit."""

import json
import subprocess
import sys

from conftest import ASSETS, REPO_ROOT, SCRIPTS

EXAMPLE = ASSETS / "paper-template" / "example.tex"
COVER_EXAMPLE = ASSETS / "paper-template" / "example-with-identity-cover.tex"


def test_submission_audit_accepts_formal_sample_without_ai_use():
    """The formal sample has a cover; all following pages remain anonymous."""
    assert EXAMPLE.is_file(), f"missing example.tex: {EXAMPLE}"
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPTS / "submission_audit.py"),
            "--paper",
            str(EXAMPLE),
            "--ai-used",
            "none",
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 0, f"unexpected exit code: {proc.returncode}\n{proc.stderr}"
    out = json.loads(proc.stdout)
    assert out["passed"] is True
    descs = " ".join(check["desc"] for check in out["checks"])
    assert "身份" in descs and "AI" in descs


def test_submission_audit_accepts_explicit_cover_entry():
    """The explicitly named compatibility entry is also a formal submission."""
    assert COVER_EXAMPLE.is_file(), f"missing cover example: {COVER_EXAMPLE}"
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPTS / "submission_audit.py"),
            "--paper",
            str(COVER_EXAMPLE),
            "--ai-used",
            "none",
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["passed"] is True
    assert any(check["ok"] and "封皮" in check["desc"] for check in out["checks"])


def test_submission_audit_rejects_identity_after_cover(tmp_path):
    """Identity text outside the permitted cover must fail."""
    leaked = tmp_path / "leaked.tex"
    text = EXAMPLE.read_text(encoding="utf-8")
    text = text.replace(r"\section{问题重述}", "学校：测试大学\n" + r"\section{问题重述}")
    leaked.write_text(text, encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPTS / "submission_audit.py"),
            "--paper",
            str(leaked),
            "--ai-used",
            "none",
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert proc.returncode == 1
    out = json.loads(proc.stdout)
    assert out["passed"] is False
    assert any(not check["ok"] and "封皮之后" in check["desc"] for check in out["checks"])
