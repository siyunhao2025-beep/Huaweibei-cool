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


def test_first_use_card_is_direct_and_does_not_restore_removed_three_steps_copy():
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    combined = skill + "\n" + readme
    for field in ("比赛届次", "你的学校是：", "参赛队号是：", "队员 1：", "队员 2：", "队员 3：", "A / B / C / D / E / F / 未定"):
        assert field in combined
    assert "下一步三件事" not in combined
    assert "请先核对参赛信息是否齐全" not in combined


def test_framework_figure_policy_has_no_stale_mandatory_tikz_or_every_paper_rule():
    tracked = [
        REPO_ROOT / "SKILL.md",
        REPO_ROOT / "README.md",
        *sorted((REPO_ROOT / "modules").glob("*.md")),
        REPO_ROOT / "assets" / "paper-template" / "华为杯_论文章节规范.md",
        REPO_ROOT / "assets" / "scaffold" / "题目" / "读题审计报告模板.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in tracked)
    assert "所有流程图必须使用 TikZ" not in combined
    assert "流程图/结构图是绝对主力，每篇必有" not in combined
    assert "复杂多问论文通常把论文级总流程图作为图1" not in combined
    assert "复杂多问论文默认从“图1 论文级总流程图”起排" not in combined
    roadmap = (REPO_ROOT / "modules" / "technical-roadmap.md").read_text(encoding="utf-8")
    assert "YAML 结构草图分支" in roadmap
    assert "任何 YAML 渲染脚本都不得覆盖这张正式 F01" in roadmap
    assert "复杂论文正式 F01 不设 500KB 人为上限" in roadmap


def test_every_figure_requires_evidence_reason_implication_and_boundary():
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    figures = (REPO_ROOT / "modules" / "figures-interface.md").read_text(encoding="utf-8")
    writing = (REPO_ROOT / "modules" / "paper-writing.md").read_text(encoding="utf-8")
    polishing = (REPO_ROOT / "modules" / "polishing.md").read_text(encoding="utf-8")
    template = (
        REPO_ROOT / "assets" / "paper-template" / "章节模板" / "通用正文模板.tex"
    ).read_text(encoding="utf-8")

    assert "每张图都必须解释“为什么”" in skill
    for text in (figures, writing, polishing, template):
        assert "原因/机制" in text
        assert "含义" in text
        assert "边界" in text
    assert "禁止偷换为因果" in figures
    assert "复合图" in figures and "流程图/框架图" in figures


def test_complex_framework_figure_requires_chinese_text_and_final_scale_qa():
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    roadmap = (REPO_ROOT / "modules" / "technical-roadmap.md").read_text(encoding="utf-8")
    figures = (REPO_ROOT / "modules" / "figures-interface.md").read_text(encoding="utf-8")
    polishing = (REPO_ROOT / "modules" / "polishing.md").read_text(encoding="utf-8")
    combined = "\n".join((skill, roadmap, figures, polishing))

    assert "中文优先、符号忠实、最终尺度可读" in skill
    assert "S1" in roadmap and "S4" in roadmap and "visible_text_contract" in roadmap
    assert "consumer-side" in combined
    assert "不得把它命名为 S6" in roadmap
    assert "普通结果图" in figures and "英文稿保持英文" in figures
    for threshold in ("11 pt", "10 pt", "9 pt"):
        assert threshold in combined
    for gate in ("乱码", "文字碰撞", "箭头遮挡", "边界溢出", "裁切"):
        assert gate in combined
    assert "audit_framework_figure.py" in skill


def test_references_and_appendix_have_separate_page_contract():
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    writing = (REPO_ROOT / "modules" / "paper-writing.md").read_text(encoding="utf-8")
    polishing = (REPO_ROOT / "modules" / "polishing.md").read_text(encoding="utf-8")
    example = (REPO_ROOT / "assets" / "paper-template" / "example.tex").read_text(encoding="utf-8")
    identity_example = (
        REPO_ROOT / "assets" / "paper-template" / "example-with-identity-cover.tex"
    ).read_text(encoding="utf-8")

    assert "参考文献与附录必须分别另起一页" in skill
    assert "参考文献另起一页" in writing
    assert "附录另起一页" in writing
    assert "参考文献与附录" in polishing and "另起一页" in polishing
    assert r"\clearpage" in example
    assert r"\clearpage" in identity_example


def test_computational_appendix_requires_traceable_code_style_pseudocode():
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    writing = (REPO_ROOT / "modules" / "paper-writing.md").read_text(encoding="utf-8")
    polishing = (REPO_ROOT / "modules" / "polishing.md").read_text(encoding="utf-8")
    appendix_template = (
        REPO_ROOT / "assets" / "paper-template" / "章节模板" / "附录模板.tex"
    ).read_text(encoding="utf-8")
    audit = (REPO_ROOT / "scripts" / "audit_tex.py").read_text(encoding="utf-8")

    assert "计算型论文的附录必须有可追溯的代码式伪代码" in skill
    for text in (writing, polishing, appendix_template):
        assert "代码式伪代码" in text
        assert "实际脚本/函数" in text
        assert "结果文件" in text
    assert "appendix_has_code_style_pseudocode" in audit
    assert "appendix_pseudocode_is_traceable" in audit


def test_numbered_problem_sections_require_reader_orienting_openers():
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    writing = (REPO_ROOT / "modules" / "paper-writing.md").read_text(encoding="utf-8")
    solving = (REPO_ROOT / "modules" / "solving.md").read_text(encoding="utf-8")
    polishing = (REPO_ROOT / "modules" / "polishing.md").read_text(encoding="utf-8")
    template = (
        REPO_ROOT / "assets" / "paper-template" / "章节模板" / "问题章节模板.tex"
    ).read_text(encoding="utf-8")
    audit = (REPO_ROOT / "scripts" / "audit_tex.py").read_text(encoding="utf-8")

    assert "每个编号问题先导读，再进入技术细节" in skill
    assert "回溯—路线—交付" in writing
    assert "每问启动：先回溯，再求解" in solving
    assert "首个小标题、公式或图表前" in polishing
    assert "REPLACE_WITH_ACTUAL_QUESTION_GUIDE" in template
    assert "question_sections_open_with_recap_route_and_deliverable" in audit


def test_adaptive_task_mapping_scaffold_is_routed_without_fixed_problem_archetypes():
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    writing = (REPO_ROOT / "modules" / "paper-writing.md").read_text(encoding="utf-8")
    mapping = (REPO_ROOT / "docs" / "TEMPLATE_CONTENT_MAPPING_23RD.md").read_text(
        encoding="utf-8"
    )
    scaffold = (
        REPO_ROOT
        / "assets"
        / "paper-template"
        / "章节模板"
        / "任务映射与总体分析模板.tex"
    ).read_text(encoding="utf-8")

    route = "assets/paper-template/章节模板/任务映射与总体分析模板.tex"
    assert route in skill and route in writing
    assert "任务映射与总体分析模板.tex" in mapping
    for field in ("输入与硬约束", "数学任务", "输出与成功条件", "真实依赖"):
        assert field in scaffold
    for guard in ("按真实问题数增删", "强造接口", "简单题直接进入"):
        assert guard in scaffold
    assert "问题一做结构识别" not in scaffold
    assert "问题二做预测" not in scaffold
    assert "问题三做优化" not in scaffold


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
    windows_user_path = re.compile(
        re.escape("C:" + "\\Users\\") + r"(?P<user>[^\\/\s<>]+)", re.IGNORECASE
    )
    allowed_example_users = {"张三", "exampleuser", "username", "user", "用户"}
    legacy_client = "Dou" + "bao"
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
        personal_users = {
            match.group("user")
            for match in windows_user_path.finditer(text)
            if match.group("user").casefold()
            not in {value.casefold() for value in allowed_example_users}
        }
        if personal_users or legacy_client in text:
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


def test_quickstart_declares_packages_for_extended_tables():
    source = (REPO_ROOT / "docs" / "examples" / "quickstart" / "main.tex").read_text(
        encoding="utf-8"
    )
    if r"\begin{tabularx}" in source:
        assert r"\usepackage{tabularx}" in source


def test_final_release_requires_full_rerun_clean_build_and_atomic_artifact_sync():
    skill = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    submission = (REPO_ROOT / "modules" / "submission.md").read_text(encoding="utf-8")
    changes = (REPO_ROOT / "modules" / "change-management.md").read_text(encoding="utf-8")
    polishing = (REPO_ROOT / "modules" / "polishing.md").read_text(encoding="utf-8")
    phases = (REPO_ROOT / "modules" / "phases.md").read_text(encoding="utf-8")
    gates = (REPO_ROOT / "docs" / "PHASE_GATES.md").read_text(encoding="utf-8")

    assert "全链同源、可回退、原子交付" in skill
    for text in (skill, submission, changes, polishing, phases, gates):
        assert "派生缓存" in text
        assert "全量重跑" in text
    assert "隔离目录干净构建" in submission
    assert "固定 DPI" in submission
    assert "解压源码包再次编译" in submission
    assert "图表生成目录与 LaTeX 读取目录分离" in changes
    assert "PDF 原始字节" in skill
    assert "内部审阅稿" in skill
