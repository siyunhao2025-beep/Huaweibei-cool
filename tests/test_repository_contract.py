# -*- coding: utf-8 -*-
"""Repository-wide contracts that prevent documentation and routing drift."""
from __future__ import annotations

import os
import re
import subprocess
import sys

from conftest import REPO_ROOT, SCRIPTS


def test_every_module_is_nonempty_and_listed_in_skill():
    modules = sorted((REPO_ROOT / "modules").glob("*.md"))
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert len(modules) == 21
    assert f"{len(modules)} 个任务契约模块" in skill
    missing = [path.name for path in modules if f"`modules/{path.name}`" not in skill]
    empty = [path.name for path in modules if not path.read_text(encoding="utf-8").strip()]
    assert not missing, f"SKILL.md 未路由模块: {missing}"
    assert not empty, f"空模块: {empty}"


def test_literal_local_references_from_skill_and_modules_exist():
    sources = [REPO_ROOT / "SKILL.md", *sorted((REPO_ROOT / "modules").glob("*.md"))]
    pattern = re.compile(
        r"`((?:modules|docs|scripts|assets|config|playbooks|tracks)/[^`]+)`"
    )
    missing: list[str] = []
    for source in sources:
        for raw in pattern.findall(source.read_text(encoding="utf-8")):
            if any(char in raw for char in "<>*{}") or any(char.isspace() for char in raw):
                continue
            target = raw.split("#", 1)[0].rstrip("/.,;：，。")
            if not (REPO_ROOT / target).exists():
                missing.append(f"{source.relative_to(REPO_ROOT)} -> {target}")
    assert not missing, "失效的仓库内引用:\n" + "\n".join(missing)


def test_distributed_files_do_not_embed_person_specific_windows_paths():
    forbidden = ("C:" + "\\Users\\ASUS", "Dou" + "bao")
    suffixes = {".md", ".py", ".tex", ".json", ".yml", ".yaml", ".txt"}
    excluded_parts = {
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "_work",
        "tmp",
    }
    hits: list[str] = []
    if (REPO_ROOT / ".git").is_dir():
        listed = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=REPO_ROOT
        ).decode("utf-8").split("\0")
        candidates = (REPO_ROOT / relative for relative in filter(None, listed))
    else:
        candidates = REPO_ROOT.rglob("*")
    for path in candidates:
        relative = path.relative_to(REPO_ROOT)
        if (
            not path.is_file()
            or path.suffix.lower() not in suffixes
            or excluded_parts.intersection(relative.parts)
        ):
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if any(token in text for token in forbidden):
            hits.append(str(relative))
    assert not hits, f"分发文件含个人机器路径/旧客户端绑定: {hits}"


def test_corpus_builder_requires_explicit_source_root():
    env = os.environ.copy()
    env.pop("HUAWEI_CORPUS_ROOT", None)
    process = subprocess.run(
        [sys.executable, str(SCRIPTS / "corpus_build.py")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert process.returncode == 2
    assert "--corpus-root" in process.stderr


def test_quickstart_demo_has_no_silent_skip_or_stale_pdf_pass():
    script = (SCRIPTS / "quickstart_demo.ps1").read_text(encoding="utf-8-sig")
    assert "[跳过]" not in script
    assert "Remove-Item -LiteralPath $pdfWork" in script
    assert "$xelatexExit -ne 0" in script
    assert "路线图必须同时生成非空 PNG 与 PDF" in script
