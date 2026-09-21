# -*- coding: utf-8 -*-
"""Smoke-test the official-format submission audit against the anonymous sample."""

import json
import subprocess
import sys

from conftest import ASSETS, REPO_ROOT, SCRIPTS

EXAMPLE = ASSETS / "paper-template" / "example.tex"
COVER_EXAMPLE = ASSETS / "paper-template" / "example-with-identity-cover.tex"


def test_submission_audit_accepts_anonymous_sample_without_ai_use():
    """An anonymous sample with no AI use must pass; disclosure is conditional."""
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


def test_submission_audit_rejects_identity_cover_sample():
    """The opt-in administrative cover must never pass as an anonymous paper."""
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
    assert proc.returncode == 1
    out = json.loads(proc.stdout)
    assert out["passed"] is False
    assert any(not check["ok"] and "身份" in check["desc"] for check in out["checks"])
