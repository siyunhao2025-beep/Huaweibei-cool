# -*- coding: utf-8 -*-
"""test_audit_tex.py — audit_tex.py 运行不报错烟雾测试。

构造一个最小 LaTeX 工程（manifest + main.tex + abstract.tex + ch1.tex），
运行 audit_tex.py，断言：退出码为 0 或 1（FAIL 也算正常产出），
且 report.json 被生成、可解析、含 checks 列表。
"""
import json
import subprocess
import sys

import audit_tex

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
                "appendix_pseudocode": {
                    "required": False,
                    "reason": "本烟雾测试仅检查纯解析文本，不涉及程序求解。",
                },
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


def _terminal_checks(tmp_path, chapters, main_inputs):
    (tmp_path / "abstract.tex").write_text("摘要正文。\n", encoding="utf-8")
    for chapter in chapters:
        (tmp_path / chapter["tex_path"]).write_text(
            rf"\section{{{chapter['title']}}}" + "\n正文。\n",
            encoding="utf-8",
        )
    manifest = {
        "title": "模型研究",
        "keywords": ["建模", "验证", "优化"],
        "abstract_tex_path": "abstract.tex",
        "appendix_pseudocode": {
            "required": False,
            "reason": "本测试为纯解析推导，不依赖程序求解。",
        },
        "chapters": chapters,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    main_path = tmp_path / "main.tex"
    main_path.write_text(
        "\\documentclass{article}\n\\begin{document}\n"
        "\\input{abstract.tex}\n"
        + "\n".join(main_inputs)
        + "\n\\end{document}\n",
        encoding="utf-8",
    )
    report = audit_tex.audit(manifest_path, main_path)
    return {
        item["code"]: item
        for item in report["checks"]
        if item["code"] in {
            "manifest_has_exactly_one_references_chapter",
            "references_and_appendices_start_new_pages",
        }
    }


def test_terminal_source_page_gate_requires_one_reference_and_clearpage(tmp_path):
    body = {
        "chapter_id": "body",
        "title": "问题重述",
        "role": "problem",
        "order": 1,
        "tex_path": "body.tex",
    }
    references = {
        "chapter_id": "refs",
        "title": "参考文献",
        "role": "references",
        "order": 2,
        "tex_path": "references.tex",
    }
    checks = _terminal_checks(
        tmp_path,
        [body, references],
        [r"\input{body.tex}", r"\clearpage", r"\input{references.tex}"],
    )
    assert checks["manifest_has_exactly_one_references_chapter"]["ok"] is True
    assert checks["references_and_appendices_start_new_pages"]["ok"] is True


def test_terminal_source_page_gate_rejects_empty_terminal_roles(tmp_path):
    body = {
        "chapter_id": "body",
        "title": "问题重述",
        "role": "problem",
        "order": 1,
        "tex_path": "body.tex",
    }
    checks = _terminal_checks(tmp_path, [body], [r"\input{body.tex}"])
    assert checks["manifest_has_exactly_one_references_chapter"]["ok"] is False
    assert checks["references_and_appendices_start_new_pages"]["ok"] is False


def test_terminal_source_page_gate_rejects_missing_clearpage(tmp_path):
    body = {
        "chapter_id": "body",
        "title": "问题重述",
        "role": "problem",
        "order": 1,
        "tex_path": "body.tex",
    }
    references = {
        "chapter_id": "refs",
        "title": "参考文献",
        "role": "references",
        "order": 2,
        "tex_path": "references.tex",
    }
    checks = _terminal_checks(
        tmp_path,
        [body, references],
        [r"\input{body.tex}", r"\input{references.tex}"],
    )
    assert checks["manifest_has_exactly_one_references_chapter"]["ok"] is True
    assert checks["references_and_appendices_start_new_pages"]["ok"] is False


def test_terminal_source_page_gate_rejects_duplicate_reference_roles(tmp_path):
    references = [
        {
            "chapter_id": f"refs-{index}",
            "title": f"参考文献{index}",
            "role": "references",
            "order": index,
            "tex_path": f"references-{index}.tex",
        }
        for index in (1, 2)
    ]
    checks = _terminal_checks(
        tmp_path,
        references,
        [
            r"\clearpage",
            r"\input{references-1.tex}",
            r"\clearpage",
            r"\input{references-2.tex}",
        ],
    )
    assert checks["manifest_has_exactly_one_references_chapter"]["ok"] is False
    assert checks["references_and_appendices_start_new_pages"]["ok"] is False
