# -*- coding: utf-8 -*-
"""test_paper_checklist.py — Wave6-A 自检表机检脚本与资产测试。"""
import json
import subprocess
import sys
from pathlib import Path

import paper_checklist

from conftest import ASSETS, REPO_ROOT, SCRIPTS

CHECKLIST_JSON = ASSETS / "checklists" / "paper_checklist.json"
CHECKLIST_MD = ASSETS / "checklists" / "优秀论文自检表.md"
PASS_TEX = Path(__file__).resolve().parent / "fixtures" / "checklist_pass.tex"
FAIL_TEX = Path(__file__).resolve().parent / "fixtures" / "checklist_fail.tex"
SCRIPT = SCRIPTS / "paper_checklist.py"


def _run(args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd or REPO_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )


# --------------------------------------------------------------------------- #
# 资产
# --------------------------------------------------------------------------- #
def test_checklist_json_parseable_and_138():
    d = json.loads(CHECKLIST_JSON.read_text(encoding="utf-8"))
    assert d["total"] == 138
    assert len(d["items"]) == 138
    ids = [it["id"] for it in d["items"]]
    assert len(set(ids)) == 138, "id 必须唯一"
    # 关键章节齐全
    sections = {it["section"] for it in d["items"]}
    for sec in ["全局格式", "摘要", "模型求解", "参考文献"]:
        assert sec in sections
    # 旧截图的三处转录记录已闭合；当前语义由纠错后的 item 字段承载。
    notes = {it["id"]: it.get("notes") for it in d["items"]}
    assert notes["M14"] is None
    assert notes["I02"] is None
    assert notes["V05"] is None
    by_id = {it["id"]: it for it in d["items"]}
    assert "服从数据结构" in by_id["V05"]["item"]
    assert by_id["V05"]["applicable_archetypes"] == [
        "classification-cv", "prediction", "spatial-graph"
    ]
    for sid in ["B12", "H04", "H05", "Q02", "Q09", "E01", "E03", "E05", "R02"]:
        assert by_id[sid]["check_method"] == "manual"


def test_checklist_md_exists_and_has_execution_requirements():
    txt = CHECKLIST_MD.read_text(encoding="utf-8")
    assert "## 执行要求" in txt
    assert "全量闭环" in txt
    assert "不等于强行让 138 项全部通过" in txt
    # 不得出现具体商业 AI 产品名
    for banned in ["claude", "chatgpt", "Claude", "ChatGPT"]:
        assert banned not in txt
    # 138 条勾选行
    assert txt.count("- [ ] ") == 138


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_help_exit_zero():
    p = _run(["--help"])
    assert p.returncode == 0, p.stderr


def test_strict_without_document_fails_closed():
    p = _run(["--strict"])
    assert p.returncode == 2
    assert "必须同时提供 --tex 或 --docx" in p.stderr


# --------------------------------------------------------------------------- #
# 正例 fixture
# --------------------------------------------------------------------------- #
def test_pass_fixture_zero_fail(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    p = _run(["--tex", str(PASS_TEX), "--problems", "2",
              "--archetype", "optimization", "--outdir", str(outdir)])
    assert p.returncode == 0, f"pass fixture 应退出 0，实际 {p.returncode}\n{p.stdout}\n{p.stderr}"
    report = (outdir / "论文自检表_已勾选.md").read_text(encoding="utf-8")
    # 机检条目全 ✅：不应有任何 "- ❌" 行（统计行里的 "❌ N" 不算）
    fail_lines = [ln for ln in report.splitlines() if ln.startswith("- ❌")]
    assert not fail_lines, f"正例 fixture 不应有 ❌：{fail_lines}"
    # 关键机检项
    for sid in ["Q03", "Q04", "S03", "S04", "A02", "A10", "V04"]:
        assert f"✅ **{sid}**" in report, f"正例 {sid} 应 ✅"


# --------------------------------------------------------------------------- #
# 反例 fixture
# --------------------------------------------------------------------------- #
def test_fail_fixture_detects_all_planted_errors(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    p = _run(["--tex", str(FAIL_TEX), "--problems", "2",
              "--archetype", "optimization", "--outdir", str(outdir)])
    assert p.returncode == 1, f"fail fixture 应退出 1，实际 {p.returncode}"
    report = (outdir / "论文自检表_已勾选.md").read_text(encoding="utf-8")
    # 每个故意埋的错误至少对应一条 ❌
    expected = {
        "Q04": "图表未引用",
        "Q03": "纯英文题注",
        "S03": "符号表没有真实数据行",
        "S04": "符号表前缺少正文引用",
        "V04": "优化检验缺少适配证据",
    }
    for sid, why in expected.items():
        assert f"❌ **{sid}**" in report, f"反例应检出 {sid}（{why}）"
    for retired_false_positive in ["R02", "Q02", "Q09", "H05", "E03"]:
        assert f"❌ **{retired_false_positive}**" not in report


def test_abstract_checks_support_production_environment_and_missing_keywords():
    def results(source, problems=None):
        sections, _ = paper_checklist.split_sections(source)
        ctx = paper_checklist.PaperContext(
            tex_path=None,
            docx_path=None,
            tex_text=source,
            sections=sections,
            problems=problems,
        )
        return {item.item_id: item for item in paper_checklist.check_a_series(ctx)}

    production = (
        r"\documentclass{gmcmthesis}\begin{document}\maketitle"
        r"\begin{abstract}针对问题一，建立可复核模型并报告结果。"
        r"\keywords{建模\quad 验证\quad 优化}\end{abstract}"
        r"\section{问题重述}正文\end{document}"
    )
    passed = results(production, problems=1)
    assert passed["A02"].status == "pass"
    assert passed["A10"].status == "pass"

    missing_keywords = production.replace(r"\keywords{建模\quad 验证\quad 优化}", "")
    failed = results(missing_keywords, problems=1)
    assert failed["A02"].status == "pass"
    assert failed["A10"].status == "fail"

    incomplete = results(production, problems=4)
    assert incomplete["A02"].status == "fail"
    assert "2、3、4" in incomplete["A02"].evidence
    assert "已识别：1" in incomplete["A02"].evidence


def test_a10_rejects_bad_keyword_counts_and_duplicates_but_accepts_three_or_six():
    def a10(keyword_command):
        source = (
            r"\documentclass{gmcmthesis}\begin{document}\maketitle"
            r"\begin{abstract}针对 Q1，建立模型并报告结果。"
            + keyword_command
            + r"\end{abstract}\section{问题重述}正文\end{document}"
        )
        sections, _ = paper_checklist.split_sections(source)
        ctx = paper_checklist.PaperContext(
            tex_path=None,
            docx_path=None,
            tex_text=source,
            sections=sections,
            problems=1,
        )
        return {item.item_id: item for item in paper_checklist.check_a_series(ctx)}["A10"]

    invalid = {
        r"\keywords{}": "内容非空",
        r"\keywords{建模}": "共 1 个",
        r"\keywords{一；二；三；四；五；六；七}": "共 7 个",
        r"\keywords{建模；验证；优化；建模}": "重复项",
    }
    for command, expected in invalid.items():
        result = a10(command)
        assert result.status == "fail", (command, result)
        assert expected in result.evidence

    for command, expected_count in (
        (r"\keywords{建模\quad验证，优化}", 3),
        (r"\keywords{一；二;三，四,五\qquad六}", 6),
    ):
        result = a10(command)
        assert result.status == "pass", (command, result)
        assert f"共 {expected_count} 个" in result.evidence


def test_docx_only_marks_tex_dependent_checks_pending(tmp_path):
    docx = tmp_path / "paper.docx"
    docx.write_bytes(b"placeholder; paper_checklist does not parse DOCX")
    outdir = tmp_path / "out"
    outdir.mkdir()

    p = _run(["--docx", str(docx), "--outdir", str(outdir)])

    assert p.returncode == 0, p.stderr
    report = (outdir / "论文自检表_已勾选.md").read_text(encoding="utf-8")
    for sid in ["Q03", "Q04", "S03", "S04"]:
        assert f"☐ **{sid}**" in report
        assert f"✅ **{sid}**" not in report
        assert f"❌ **{sid}**" not in report
    assert "scripts/audit_docx.py" in report
    assert "DOCX 请另运行 scripts/audit_docx.py" in p.stderr

    checklist = json.loads(CHECKLIST_JSON.read_text(encoding="utf-8"))
    decisions = {
        item["id"]: {"status": "pass", "note": "测试裁决"}
        for item in checklist["items"]
        if item["check_method"] == "manual"
    }
    (outdir / "paper_checklist_decisions.json").write_text(
        json.dumps(decisions, ensure_ascii=False),
        encoding="utf-8",
    )
    strict_docx = _run(["--docx", str(docx), "--outdir", str(outdir), "--strict"])
    assert strict_docx.returncode == 1
    assert "机检项目处于 pending" in strict_docx.stderr

    strict_missing_tex = _run(
        ["--tex", str(tmp_path / "missing.tex"), "--outdir", str(outdir), "--strict"]
    )
    assert strict_missing_tex.returncode == 1
    assert "机检项目处于 pending" in strict_missing_tex.stderr


def test_q04_only_binds_figure_and_table_labels():
    def result(source):
        return paper_checklist.check_q04(
            paper_checklist.PaperContext(tex_path=None, docx_path=None, tex_text=source)
        )

    assert result(r"\section{正文}\label{sec:unused} 无图表。").status == "pass"
    assert result(r"\begin{figure}\caption{示意图}\end{figure}").status == "fail"
    assert result(
        r"\begin{table}\caption{结果}\label{tab:r}内容\end{table}"
    ).status == "fail"
    passed = result(
        r"结果见表\ref{tab:r}。"
        r"\begin{table}\caption{结果}\label{tab:r}内容\end{table}"
    )
    assert passed.status == "pass"

    wrapped = result(
        r"\newcommand{\evidencefigure}[3]{"
        r"\begin{figure}\caption{#2}\label{#3}\end{figure}}"
        r"结果见图\ref{fig:a}。\evidencefigure{a.png}{结果图 A}{fig:a}"
        r"结果见图\ref{fig:b}。\frameworkfigure{b.png}{框架图 B}{fig:b}"
    )
    assert wrapped.status == "pass", wrapped.evidence


def test_q03_checks_wrapper_call_captions_and_ignores_inactive_or_template_text():
    def result(source):
        return paper_checklist.check_q03(
            paper_checklist.PaperContext(tex_path=None, docx_path=None, tex_text=source)
        )

    definition = (
        r"\newcommand{\evidencefigure}[3]{"
        r"\begin{figure}\caption{#2}\label{#3}\end{figure}}"
    )
    assert result(
        definition
        + r"\evidencefigure{a.png}{中文结果图}{fig:a}"
        + r"\iffalse\begin{figure}\caption{English hidden}\end{figure}\fi"
    ).status == "pass"
    assert result(
        definition + r"\evidencefigure{a.png}{English only}{fig:a}"
    ).status == "fail"


def test_q03_q04_cover_roadmap_and_custom_figure_wrappers():
    def q03(source):
        return paper_checklist.check_q03(
            paper_checklist.PaperContext(tex_path=None, docx_path=None, tex_text=source)
        )

    def q04(source):
        return paper_checklist.check_q04(
            paper_checklist.PaperContext(tex_path=None, docx_path=None, tex_text=source)
        )

    roadmap = (
        r"结果见图\ref{fig:r}。"
        r"\roadmapfigure{a.png}{中文总体路线图}{fig:r}"
    )
    assert q03(roadmap).status == "pass"
    assert q04(roadmap).status == "pass"
    assert q03(r"\roadmapfigure{a.png}{ASCII CAPTION}{fig:r}").status == "fail"
    assert q04(r"\roadmapfigure{a.png}{中文总体路线图}{fig:r}").status == "fail"

    custom = (
        r"\documentclass{article}"
        r"\newcommand{\paperfigure}[2]{"
        r"\begin{figure}\caption{#1}\label{#2}\end{figure}}"
        r"\begin{document}结果见图\ref{fig:c}。"
        r"\paperfigure{中文自定义结果图}{fig:c}\end{document}"
    )
    assert q03(custom).status == "pass"
    assert q04(custom).status == "pass"
    assert q03(custom.replace("中文自定义结果图", "English only")).status == "fail"
    assert q03(
        r"\begin{figure}\caption[Short]{ASCII LONG CAPTION}"
        r"\label{fig:a}\end{figure}"
    ).status == "fail"
    assert q03(
        r"\begin{figure}\caption{ASCII $Z_{DR}$ CAPTION}"
        r"\label{fig:nested}\end{figure}"
    ).status == "fail"


def test_checklist_expands_inputs_relative_to_main_with_project_boundary(tmp_path):
    project = tmp_path / "project"
    paper = project / "paper"
    chapters = project / "chapters"
    paper.mkdir(parents=True)
    chapters.mkdir()
    (project / "比赛配置.json").write_text("{}", encoding="utf-8")
    (chapters / "part.tex").write_text("父级片段内容", encoding="utf-8")
    main = paper / "main.tex"
    main.write_text(r"开始\input{../chapters/part}结束", encoding="utf-8")

    root = paper_checklist.find_project_root(main.parent)
    expanded, errors = paper_checklist.expand_tex_in_order(main, root, base=main.parent)
    assert errors == []
    assert "开始" in expanded and "父级片段内容" in expanded and "结束" in expanded

    outside = tmp_path / "outside.tex"
    outside.write_text("越界内容", encoding="utf-8")
    main.write_text(r"\input{../../outside}", encoding="utf-8")
    _, errors = paper_checklist.expand_tex_in_order(main, root, base=main.parent)
    assert errors


# --------------------------------------------------------------------------- #
# sidecar 与 --strict
# --------------------------------------------------------------------------- #
def test_mark_persists_and_strict_gate(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    # 先跑一次，此时人工条目未裁决，--strict 应失败
    p = _run(["--tex", str(PASS_TEX), "--problems", "2",
              "--archetype", "optimization", "--outdir", str(outdir), "--strict"])
    assert p.returncode == 1, "未裁决人工条目时 --strict 应失败"
    # --mark 一批人工条目
    p = _run(["--tex", str(PASS_TEX), "--outdir", str(outdir),
              "--mark", "F01=pass", "--mark", "F02=pass", "--mark", "F03=pass",
              "--mark", "F04=pass", "--mark", "F05=pass", "--mark", "F06=pass",
              "--mark", "T06=pass", "--mark", "Q08=na", "--note", "全部图表均有正文引用"])
    assert p.returncode == 0, p.stderr
    dec = json.loads((outdir / "paper_checklist_decisions.json").read_text(encoding="utf-8"))
    assert dec["F01"]["status"] == "pass"
    assert dec["Q08"]["status"] == "na"
    assert "图表" in dec["Q08"]["note"]

    unknown = _run([
        "--tex", str(PASS_TEX), "--outdir", str(outdir),
        "--mark", "NOT_A_CHECK=pass",
    ])
    assert unknown.returncode == 2
    assert "未知自检项" in unknown.stderr

    machine_override = _run([
        "--tex", str(PASS_TEX), "--outdir", str(outdir),
        "--mark", "Q03=pass",
    ])
    assert machine_override.returncode == 2
    assert "机检项不得" in machine_override.stderr

    unexplained_na = _run([
        "--tex", str(PASS_TEX), "--outdir", str(outdir),
        "--mark", "F01=na",
    ])
    assert unexplained_na.returncode == 2
    assert "必须给出具体理由" in unexplained_na.stderr


# --------------------------------------------------------------------------- #
# contest_init 集成
# --------------------------------------------------------------------------- #
def test_contest_init_copies_checklist(tmp_path, monkeypatch):
    import contest_init
    workdir = tmp_path / "work"
    contest_init.init_workdir(workdir)
    target = workdir / "论文" / "优秀论文自检表.md"
    assert target.exists(), f"contest_init 未复制自检表到 {target}"
    config = workdir / "config" / "contest.json"
    assert config.exists(), f"contest_init 未复制比赛配置到 {config}"
    data = json.loads(config.read_text(encoding="utf-8"))
    assert data["paper"]["internal_total_page_target"]["mode"] == "user_decides"
    assert "执行要求" in target.read_text(encoding="utf-8")
