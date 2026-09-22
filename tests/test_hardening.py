# -*- coding: utf-8 -*-
"""Regression tests for security boundaries and honest QA reporting."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import REPO_ROOT, SCRIPTS


FIGURE_SCRIPTS = REPO_ROOT / "skills" / "academic-figure" / "scripts"


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_r_png_device_quotes_untrusted_output_path():
    compose = load_script("hardening_compose", FIGURE_SCRIPTS / "compose.py")
    malicious = 'panel"); system("whoami"); #\\next.png'
    expected_literal = json.dumps(malicious.replace("\\", "/"), ensure_ascii=False)
    call = compose.r_png_device({"width_mm": 65, "height_mm": 40, "dpi": 300}, malicious)
    assert call.startswith(f"png({expected_literal}, ")
    assert "eval(parse" not in call


def test_markdown_migration_rejects_missing_abstract_and_source_escape(tmp_path):
    migration = load_script("hardening_migration", SCRIPTS / "migrate_markdown_to_tex.py")
    source = tmp_path / "legacy"
    source.mkdir()
    (source / "chapter.md").write_text("# 正文\n内容", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"chapters": [{"title": "正文", "content_file": "chapter.md"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="abstract"):
        migration.migrate(manifest, source, tmp_path / "tex")

    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {"abstract": "摘要", "chapters": [{"title": "正文", "content_file": "../outside.md"}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source-dir"):
        migration.migrate(manifest, source, tmp_path / "tex")


def test_markdown_migration_rejects_case_insensitive_output_collisions(tmp_path):
    migration = load_script("hardening_migration_collision", SCRIPTS / "migrate_markdown_to_tex.py")
    source = tmp_path / "legacy"
    source.mkdir()
    (source / "A.md").write_text("A", encoding="utf-8")
    (source / "a.md").write_text("a", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "abstract": "摘要",
                "chapters": [
                    {"title": "A", "content_file": "A.md"},
                    {"title": "a", "content_file": "a.md"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="冲突"):
        migration.migrate(manifest, source, tmp_path / "tex")


def test_word_figure_path_stays_inside_project(tmp_path):
    build_docx = load_script("hardening_build_docx", SCRIPTS / "build_docx.py")
    image = tmp_path / "figure.png"
    image.write_bytes(b"not decoded in this path-only test")
    assert build_docx.resolve_figure_path(tmp_path, "figure.png") == image.resolve()

    outside = tmp_path.parent / "outside.png"
    outside.write_bytes(b"outside")
    with pytest.raises(ValueError, match="工作目录"):
        build_docx.resolve_figure_path(tmp_path, "../outside.png")

    vector = tmp_path / "figure.svg"
    vector.write_text("<svg/>", encoding="utf-8")
    with pytest.raises(ValueError, match="不支持"):
        build_docx.resolve_figure_path(tmp_path, "figure.svg")


def test_word_derivative_builds_and_passes_package_audit(tmp_path):
    build_docx = load_script("hardening_build_docx_e2e", SCRIPTS / "build_docx.py")
    audit_docx = load_script("hardening_audit_docx_e2e", SCRIPTS / "audit_docx.py")
    (tmp_path / "abstract.tex").write_text(
        r"本研究构建 Model 1，并得到 95\% 的验证结果。", encoding="utf-8"
    )
    (tmp_path / "chapter.tex").write_text(
        r"\section{问题重述}" + "\n" + "正文包含 English 123 与可复核结论。", encoding="utf-8"
    )
    (tmp_path / "references.tex").write_text("参考来源条目。", encoding="utf-8")
    (tmp_path / "appendix.tex").write_text("复现环境与关键参数。", encoding="utf-8")
    manifest = tmp_path / "paper.json"
    manifest.write_text(
        json.dumps(
            {
                "title": "Test 模型研究",
                "keywords": ["建模", "Model"],
                "abstract_tex_path": "abstract.tex",
                "chapters": [
                    {
                        "chapter_id": "problem",
                        "title": "问题重述",
                        "role": "problem",
                        "order": 1,
                        "level": 1,
                        "tex_path": "chapter.tex",
                    },
                    {
                        "chapter_id": "refs", "title": "参考文献", "role": "references",
                        "order": 2, "level": 1, "tex_path": "references.tex",
                    },
                    {
                        "chapter_id": "appendix", "title": "附录 A 可复现代码框架", "role": "appendix",
                        "order": 3, "level": 1, "tex_path": "appendix.tex",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    config = tmp_path / "比赛配置.json"
    config.write_text(
        json.dumps(
            {"contest": {"edition_cn": "二十三", "verified_against_official_rules": True}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "paper.docx"
    build_docx.build(
        SimpleNamespace(
            input=manifest,
            template=REPO_ROOT / "assets" / "paper-template" / "研赛论文Word标准模板.docx",
            output=output,
            manifest_out=None,
            contest_config=config,
        )
    )
    report = audit_docx.audit(output)
    assert report["status"] == "PASS", json.dumps(report["failures"], ensure_ascii=False, indent=2)

    missing_heading = tmp_path / "paper_missing_appendix_heading.docx"
    original = "附录 A 可复现代码框架".encode("utf-8")
    replacement = "可复现代码框架".encode("utf-8")
    replaced = False
    with zipfile.ZipFile(output) as source, zipfile.ZipFile(missing_heading, "w") as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "word/document.xml":
                updated = data.replace(original, replacement)
                replaced = updated != data
                data = updated
            target.writestr(item, data)
    assert replaced
    missing_report = audit_docx.audit(missing_heading)
    terminal_check = next(
        item for item in missing_report["checks"]
        if item["code"] == "references_and_appendices_start_new_pages"
    )
    assert terminal_check["ok"] is False
    assert terminal_check["missing_roles"] == ["appendix"]


def test_copy_assets_validates_every_source_before_writing(tmp_path):
    build_latex = load_script("hardening_build_latex", SCRIPTS / "build_latex.py")
    template = tmp_path / "template"
    output = tmp_path / "output"
    (template / "figures").mkdir(parents=True)
    template.mkdir(exist_ok=True)
    for name in ("gmcmthesis.cls", "gmcm.bst", "reference.bib", "gmcm-title.sty"):
        (template / name).write_text(name, encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="模板资产不完整"):
        build_latex.copy_assets(template, output)
    assert not output.exists() or not any(output.iterdir())


def test_latex_builder_output_passes_source_audit(tmp_path):
    build_latex = load_script("hardening_build_latex_e2e", SCRIPTS / "build_latex.py")
    audit_tex = load_script("hardening_audit_tex_e2e", SCRIPTS / "audit_tex.py")
    (tmp_path / "abstract.tex").write_text("摘要包含可复核的主要模型与结论。", encoding="utf-8")
    (tmp_path / "chapter.tex").write_text(
        r"\section{问题重述}" + "\n" + "正文内容。", encoding="utf-8"
    )
    (tmp_path / "references.tex").write_text(
        "\n".join(
            [
                r"\begin{thebibliography}{9}",
                r"\bibitem{official} 官方格式规范。",
                r"\end{thebibliography}",
            ]
        ),
        encoding="utf-8",
    )
    valid_appendix = "\n".join(
        [
            r"\section{复现说明}",
            "对应脚本：solve.py；结果文件：results.csv。",
            r"\begin{Python}{可复现求解流程}",
            'config = read_json("config.json")',
            'data = read_csv("data.csv")',
            'train, validation, test = split_by_event(data, seed=config["seed"])',
            "model = fit(train, config)",
            "assert validate(model, validation)",
            "metrics = evaluate(model, test)",
            'write_csv(metrics, "results.csv")',
            r"\end{Python}",
        ]
    )
    (tmp_path / "appendix.tex").write_text(valid_appendix, encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "title": "模型研究",
                "keywords": ["建模", "验证"],
                "abstract_tex_path": "abstract.tex",
                "chapters": [
                    {"chapter_id": "c1", "title": "问题重述", "role": "problem", "order": 1, "tex_path": "chapter.tex"},
                    {"chapter_id": "refs", "title": "参考文献", "role": "references", "order": 2, "tex_path": "references.tex"},
                    {"chapter_id": "appendix", "title": "附录", "role": "appendix", "order": 3, "tex_path": "appendix.tex"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    config = {"contest": {"edition_cn": "二十三", "verified_against_official_rules": True}}
    manifest = build_latex.load_manifest(manifest_path)
    main_text, inputs = build_latex.build_main(manifest, tmp_path, config)
    assert inputs == ["abstract.tex", "chapter.tex", "references.tex", "appendix.tex"]
    assert r"\clearpage" + "\n" + r"\input{references.tex}" in main_text
    assert r"\clearpage" + "\n" + r"\appendix" + "\n" + r"\input{appendix.tex}" in main_text
    main_path = tmp_path / "paper.tex"
    main_path.write_text(main_text, encoding="utf-8")
    report = audit_tex.audit(manifest_path, main_path)
    assert report["status"] == "PASS", json.dumps(report["failures"], ensure_ascii=False, indent=2)

    nested_code = valid_appendix.split("\n", 1)[1]
    (tmp_path / "appendix_code.tex").write_text(nested_code, encoding="utf-8")
    (tmp_path / "appendix.tex").write_text(
        r"\section{复现说明}" + "\n" + r"\input{appendix_code.tex}",
        encoding="utf-8",
    )
    nested_report = audit_tex.audit(manifest_path, main_path)
    assert nested_report["status"] == "PASS", json.dumps(
        nested_report["failures"], ensure_ascii=False, indent=2
    )

    (tmp_path / "appendix.tex").write_text(
        r"\section{复现说明}" + "\n" + "只有文字，没有代码式伪代码。",
        encoding="utf-8",
    )
    missing_code_report = audit_tex.audit(manifest_path, main_path)
    assert "appendix_has_code_style_pseudocode" in {
        item["code"] for item in missing_code_report["failures"]
    }

    (tmp_path / "appendix.tex").write_text(
        "\n".join(
            [
                r"\section{复现说明}",
                "对应脚本：solve.py；结果文件：results.csv。",
                r"\begin{Python}{空壳}",
                'print("hello")',
                r"\end{Python}",
            ]
        ),
        encoding="utf-8",
    )
    shallow_report = audit_tex.audit(manifest_path, main_path)
    assert next(
        item for item in shallow_report["checks"]
        if item["code"] == "appendix_has_code_style_pseudocode"
    )["ok"] is True
    assert "appendix_pseudocode_is_traceable" in {
        item["code"] for item in shallow_report["failures"]
    }

    generic_chain = "\n".join(
        [
            r"\section{复现说明}",
            "对应脚本：solve.py；结果文件：results.csv。",
            r"\begin{Python}{通用占位链}",
            'config = read_json("config.json")',
            'raw = read_csv("data.csv")',
            'data = audit_and_clean(raw)',
            'features = build_features(data)',
            'baseline = fit(features)',
            'result = solve_model(baseline)',
            'metrics = evaluate(result)',
            'write_csv(metrics, "results.csv")',
            r"\end{Python}",
        ]
    )
    (tmp_path / "appendix.tex").write_text(generic_chain, encoding="utf-8")
    generic_chain_report = audit_tex.audit(manifest_path, main_path)
    generic_check = next(
        item for item in generic_chain_report["checks"]
        if item["code"] == "appendix_pseudocode_is_traceable"
    )
    assert generic_check["ok"] is False
    assert generic_check["generic_placeholder_calls"] == [
        "audit_and_clean", "build_features", "solve_model"
    ]

    mapped_chain = generic_chain.replace(
        "对应脚本：solve.py；结果文件：results.csv。",
        (
            "函数映射：preprocess.py::audit_and_clean；"
            "features.py::build_features；solve.py::solve_model；"
            "结果文件：results.csv。"
        ),
    )
    (tmp_path / "appendix.tex").write_text(mapped_chain, encoding="utf-8")
    mapped_chain_report = audit_tex.audit(manifest_path, main_path)
    assert mapped_chain_report["status"] == "PASS", json.dumps(
        mapped_chain_report["failures"], ensure_ascii=False, indent=2
    )

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["appendix_pseudocode"] = {
        "required": False,
        "reason": "本例仅验证纯解析推导，不依赖程序求解或数值实验。",
    }
    manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False), encoding="utf-8")
    waiver_report = audit_tex.audit(manifest_path, main_path)
    assert waiver_report["status"] == "PASS", json.dumps(
        waiver_report["failures"], ensure_ascii=False, indent=2
    )
    manifest_data["appendix_pseudocode"]["reason"] = "太短"
    manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False), encoding="utf-8")
    bad_waiver_report = audit_tex.audit(manifest_path, main_path)
    assert "appendix_pseudocode_policy_valid" in {
        item["code"] for item in bad_waiver_report["failures"]
    }

    manifest_data.pop("appendix_pseudocode")
    manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "appendix.tex").write_text(valid_appendix, encoding="utf-8")

    bad_main = tmp_path / "paper_missing_reference_break.tex"
    bad_main.write_text(
        main_text.replace(r"\clearpage" + "\n" + r"\input{references.tex}", r"\input{references.tex}"),
        encoding="utf-8",
    )
    bad_report = audit_tex.audit(manifest_path, bad_main)
    assert "references_and_appendices_start_new_pages" in {
        item["code"] for item in bad_report["failures"]
    }


def test_numbered_question_sections_require_progressive_openers(tmp_path):
    audit_tex = load_script("hardening_audit_tex_question_openers", SCRIPTS / "audit_tex.py")

    valid = r"""
\section{问题一：容量配置}
问题一承接题面给定的逐时负荷与设备上限，需要确定满足可靠性约束的储能容量。为避免直接使用复杂算法掩盖可行性，本问先用线性规划建立成本基线，再用蒙特卡洛场景检验极端负荷；最终给出容量、成本区间和失负荷风险，并把冻结容量传给问题二的调度模型。
\subsection{模型建立}
正文。
\section{问题二：独立校准}
问题二与问题一的容量决策相互独立，因为这里只使用观测样本校准传感器偏差。本问先估计分段误差，再用留出样本比较校准前后的绝对误差；最终输出校准曲线及置信区间，作为全文独立的质量控制结果。
\begin{equation}x=1\end{equation}
"""
    findings = audit_tex.audit_question_openers(valid)
    assert len(findings) == 2
    assert all(item["ok"] for item in findings), findings

    generic = r"""
\section{第 1 问：任务名称}
本问主要针对题目提出的问题开展相关内容分析，目标是完成问题研究。为此先分析数据，再采用合适的模型和算法完成求解；最后得到相应结果并给出结论，为后续研究提供依据。
\subsection{求解}
正文。
"""
    generic_finding = audit_tex.audit_question_openers(generic)[0]
    assert generic_finding["ok"] is False
    assert generic_finding["generic_only"] is True

    late = r"""
\section{问题3：预测}
\begin{equation}y=x\end{equation}
本问使用历史序列预测未来需求。先拟合基线再检验误差，最终给出预测区间并传给后续优化。
"""
    assert audit_tex.audit_question_openers(late)[0]["ok"] is False

    comments_only = r"""
\section{问题四：优化}
% 本问回溯输入，先建立模型，再给出结果。
\subsection{模型}
正文。
"""
    assert audit_tex.audit_question_openers(comments_only)[0]["ok"] is False
    assert audit_tex.audit_question_openers(r"\section{问题重述}\subsection{题意}正文。") == []
    assert audit_tex.audit_question_openers(
        r"\appendix\section{Q2 全部候选}\subsection{表格}正文。"
    ) == []

    (tmp_path / "opener.tex").write_text(
        "问题一使用题面给出的需求序列与容量上限，需要确定可行配置。"
        "为避免复杂算法掩盖可行性，本问先建立线性规划基线，再用场景扰动检查鲁棒性；"
        "最终给出容量和成本区间，"
        "并将冻结配置传给问题二。",
        encoding="utf-8",
    )
    (tmp_path / "question.tex").write_text(
        r"\section{问题一：配置}" + "\n" + r"\input{opener.tex}" + "\n"
        + r"\subsection{模型}" + "\n正文。",
        encoding="utf-8",
    )
    (tmp_path / "paper.tex").write_text(r"\input{question.tex}", encoding="utf-8")
    expanded, errors = audit_tex.expand_tex_in_order(tmp_path / "paper.tex", tmp_path)
    assert not errors
    assert audit_tex.audit_question_openers(expanded)[0]["ok"] is True


def test_ab_comparison_requires_complete_consistent_measurements():
    ab_test = load_script("hardening_ab_test", FIGURE_SCRIPTS / "ab_test.py")
    with pytest.raises(ValueError, match="missing scenario"):
        ab_test.validate_result_set({}, "baseline")

    payload = {}
    for scenario in ab_test.SCENARIOS:
        total = len(scenario["expected"]["checks"])
        payload[scenario["id"]] = {"passed": total, "total": total, "pass_rate": 1.0}
    assert ab_test.validate_result_set(payload, "baseline") == payload
    payload[ab_test.SCENARIOS[0]["id"]]["pass_rate"] = 0.5
    with pytest.raises(ValueError, match="inconsistent"):
        ab_test.validate_result_set(payload, "baseline")


def test_generated_source_contract_distinguishes_pass_and_fail():
    runner = load_script("hardening_e2e_runner", FIGURE_SCRIPTS / "e2e_runner.py")
    scenario = next(item for item in runner.SCENARIOS if item.id == "S4_unknown_chart")
    bad = runner.score_script("print('not a figure')", scenario)
    assert bad["meets_threshold"] is False
    good_source = """
# cross-type inherit from a network asset
CATEGORICAL = ["#2166AC"]
FONT = "Arial"
import matplotlib.pyplot as plt
plt.plot([1, 2], [2, 3])
"""
    good = runner.score_script(good_source, scenario)
    assert good["meets_threshold"] is True


def test_tex_audit_handles_escaped_percent_and_rejects_nested_escape(tmp_path):
    audit_tex = load_script("hardening_audit_tex", SCRIPTS / "audit_tex.py")
    assert audit_tex.remove_comments(r"保留 50\% 内容 % 删除注释") == r"保留 50\% 内容 "

    abstract = tmp_path / "abstract.tex"
    chapter = tmp_path / "chapter.tex"
    secret = tmp_path.parent / "secret.tex"
    abstract.write_text("摘要", encoding="utf-8")
    chapter.write_text(r"\section{正文}" + "\n" + r"\input{../secret}", encoding="utf-8")
    secret.write_text("secret", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "title": "测试",
                "keywords": ["测试"],
                "abstract_tex_path": "abstract.tex",
                "chapters": [
                    {"chapter_id": "c1", "title": "正文", "role": "problem", "order": 1, "tex_path": "chapter.tex"}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    main = tmp_path / "paper.tex"
    main.write_text(
        "\n".join(
            [
                r"\schoolname{}\baominghao{}\membera{}\memberb{}\memberc{}",
                r"\begin{document}\makeidentitycover\maketitle",
                r"\begin{abstract}\input{abstract.tex}\end{abstract}",
                r"\input{chapter.tex}",
                r"\end{document}",
            ]
        ),
        encoding="utf-8",
    )
    report = audit_tex.audit(manifest, main)
    assert report["status"] == "FAIL"
    nested = next(item for item in report["checks"] if item["code"] == "nested_inputs_are_static_and_local")
    assert nested["ok"] is False


def test_tex_audit_rejects_shell_escape_in_main(tmp_path):
    audit_tex = load_script("hardening_audit_tex_shell", SCRIPTS / "audit_tex.py")
    abstract = tmp_path / "abstract.tex"
    chapter = tmp_path / "chapter.tex"
    abstract.write_text("摘要", encoding="utf-8")
    chapter.write_text(r"\section{正文}" + "\n正文", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "title": "测试",
                "keywords": ["测试"],
                "abstract_tex_path": "abstract.tex",
                "chapters": [
                    {"chapter_id": "c1", "title": "正文", "role": "problem", "order": 1, "tex_path": "chapter.tex"}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    main = tmp_path / "paper.tex"
    main.write_text(
        "\n".join(
            [
                r"\schoolname{}\baominghao{}\membera{}\memberb{}\memberc{}",
                r"\begin{document}\makeidentitycover\maketitle",
                r"\immediate\write18{whoami}",
                r"\begin{abstract}\input{abstract.tex}\end{abstract}",
                r"\input{chapter.tex}",
                r"\end{document}",
            ]
        ),
        encoding="utf-8",
    )
    report = audit_tex.audit(manifest, main)
    dangerous = next(
        item for item in report["checks"]
        if item["code"] == "no_dangerous_tex_file_or_shell_commands"
    )
    assert report["status"] == "FAIL"
    assert dangerous["ok"] is False
    assert any("write18" in command for command in dangerous["commands"])


def test_eval_runner_unknown_type_fails_without_traceback():
    process = subprocess.run(
        [
            sys.executable,
            str(FIGURE_SCRIPTS / "eval_runner.py"),
            "--type",
            "DefinitelyMissingFigureType",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert process.returncode == 1
    assert "not found" in process.stdout.lower()
    assert "traceback" not in (process.stdout + process.stderr).lower()


def test_submission_audit_refuses_unreadable_anonymous_input(tmp_path):
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    process = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPTS / "submission_audit.py"),
            "--paper",
            str(empty),
            "--cover-policy",
            "forbidden",
            "--ai-used",
            "none",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert process.returncode == 1
    report = json.loads(process.stdout)
    assert any(not item["ok"] and "文本可读取" in item["desc"] for item in report["checks"])


def test_submission_audit_preserves_escaped_percent_but_removes_comments():
    audit = load_script("hardening_submission_comments", SCRIPTS / "submission_audit.py")
    assert audit.strip_tex_comments(r"保留 95\% 结果 % 删除注释") == r"保留 95\% 结果 "
    assert audit.strip_tex_comments(r"换行\\% 删除注释") == "换行\\\\"


def test_static_figure_audit_is_complete_without_empirical_claim():
    runner = load_script("hardening_static_ab", FIGURE_SCRIPTS / "run_ab_tests.py")
    report = runner.run_all()
    assert report["summary"]["all_passed"] is True
    assert report["empirical_quality_claim"] is False
