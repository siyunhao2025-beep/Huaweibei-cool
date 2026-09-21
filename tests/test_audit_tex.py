# -*- coding: utf-8 -*-
"""test_audit_tex.py — audit_tex.py 运行不报错烟雾测试。

构造一个最小 LaTeX 工程（manifest + main.tex + abstract.tex + ch1.tex），
运行 audit_tex.py，断言：退出码为 0 或 1（FAIL 也算正常产出），
且 report.json 被生成、可解析、含 checks 列表。
"""
import json
import subprocess
import sys


from conftest import REPO_ROOT, SCRIPTS


def test_audit_tex_runs(tmp_path):
    proj = tmp_path / "latexproj"
    proj.mkdir()
    (proj / "abstract.tex").write_text("摘要正文。\n", encoding="utf-8")
    (proj / "ch1.tex").write_text("第一章内容。\n", encoding="utf-8")
    (proj / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n"
        "\\input{abstract.tex}\n\\input{ch1.tex}\n\\end{document}\n",
        encoding="utf-8")
    manifest = {"abstract_tex_path": "abstract.tex",
                "chapters": [{"tex_path": "ch1.tex"}]}
    (proj / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    report = proj / "report.json"

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "audit_tex.py"),
         "--manifest", str(proj / "manifest.json"),
         "--main", str(proj / "main.tex"),
         "--report", str(report)],
        cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=60)

    assert proc.returncode in (0, 1), f"audit_tex 异常退出: {proc.returncode}\n{proc.stderr}"
    assert report.is_file(), "未生成 report.json"
    data = json.loads(report.read_text(encoding="utf-8"))
    assert "checks" in data and "status" in data
    assert isinstance(data["checks"], list) and len(data["checks"]) > 0
