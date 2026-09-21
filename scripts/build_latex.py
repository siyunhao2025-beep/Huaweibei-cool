#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_论文规范模板/tools/，相对路径已改为 CLI 参数驱动，Wave3 验证编译链路。
"""Build the single LaTeX paper entry point from a TeX-only manifest.

The manifest is metadata and ordering; chapter prose lives only in the
referenced ``.tex`` fragments.  This tool deliberately rejects Markdown
chapter paths and inline chapter content.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


ROLES = {"preliminary", "problem", "evaluation", "conclusion", "references", "appendix"}

def load_contest_config(start: Path, explicit: Path | None = None) -> dict:
    """Load root 比赛配置.json; official contest rules should be reflected there before paper generation."""
    if explicit is not None:
        candidate = explicit.resolve()
        if not candidate.is_file():
            raise FileNotFoundError(f"比赛配置不存在: {candidate}")
        return json.loads(candidate.read_text(encoding="utf-8-sig"))
    for base in [start.resolve(), *start.resolve().parents]:
        candidate = base / "比赛配置.json"
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8-sig"))
    raise FileNotFoundError("未找到根目录 比赛配置.json；请先运行 比赛当天初始化.bat 或指定 --contest-config")


def contest_edition(config: dict) -> str:
    contest = config.get("contest", {})
    if contest.get("verified_against_official_rules") is not True:
        raise ValueError("比赛配置中的届次尚未通过当届官方规则核对：请先更新 contest.edition_cn / edition_arabic，并将 verified_against_official_rules 设为 true")
    edition = str(contest.get("edition_cn", "")).strip()
    if not edition:
        raise ValueError("比赛配置.json 缺少 contest.edition_cn")
    return edition



def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def relative_file(root: Path, raw: str, *, label: str) -> Path:
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} 必须位于论文工作目录内: {raw}") from exc
    if candidate.suffix.lower() != ".tex":
        raise ValueError(f"{label} 必须使用 .tex: {raw}")
    if not candidate.is_file():
        raise FileNotFoundError(f"{label} 不存在: {candidate}")
    return candidate


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    required = {"title", "keywords", "abstract_tex_path", "chapters"}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"manifest 缺少字段: {', '.join(missing)}")
    forbidden = {"abstract", "content", "content_file"} & set(data)
    if forbidden:
        raise ValueError(f"LaTeX-first manifest 禁止字段: {', '.join(sorted(forbidden))}")
    if not isinstance(data["keywords"], list) or not data["keywords"]:
        raise ValueError("关键词必须至少提供一个条目")
    if any(not str(item).strip() for item in data["keywords"]):
        raise ValueError("关键词不能包含空字符串")
    if not isinstance(data["chapters"], list) or not data["chapters"]:
        raise ValueError("chapters 不能为空")
    for index, chapter in enumerate(data["chapters"], start=1):
        required_chapter = {"chapter_id", "title", "role", "order", "tex_path"}
        missing_chapter = sorted(required_chapter - set(chapter))
        if missing_chapter:
            raise ValueError(f"第 {index} 个章节缺少字段: {', '.join(missing_chapter)}")
        if chapter["role"] not in ROLES:
            raise ValueError(f"章节角色无效: {chapter['role']}")
        if "content_file" in chapter or "content" in chapter:
            raise ValueError(f"章节 {chapter['chapter_id']} 仍使用旧 content/content_file 字段")
        if str(chapter["tex_path"]).lower().endswith(".md"):
            raise ValueError(f"章节 {chapter['chapter_id']} 禁止使用 Markdown 源文件")
    orders = [int(chapter["order"]) for chapter in data["chapters"]]
    if orders != sorted(orders) or len(set(orders)) != len(orders):
        raise ValueError("章节 order 必须严格递增且不重复")
    return data


def check_fragment(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    if "\\documentclass" in text or "\\begin{document}" in text or "\\end{document}" in text:
        raise ValueError(f"章节 fragment 不得包含 document 级结构: {path}")
    if re.search(r"(?m)^\s*#{1,6}\s", text) or re.search(r"(?m)^\s*\|[^|]+\|", text) or "![" in text:
        raise ValueError(f"章节 fragment 残留 Markdown 语法: {path}")


def build_main(manifest: dict, root: Path, contest_config: dict) -> tuple[str, list[str]]:
    abstract = relative_file(root, manifest["abstract_tex_path"], label="abstract_tex_path")
    inputs = [abstract.relative_to(root).as_posix()]
    for chapter in manifest["chapters"]:
        fragment = relative_file(root, str(chapter["tex_path"]), label=f"章节 {chapter['chapter_id']}")
        check_fragment(fragment)
        inputs.append(fragment.relative_to(root).as_posix())

    raw_title = str(manifest["title"]).strip()
    title = tex_escape(raw_title)
    keywords = r"\quad ".join(tex_escape(str(item).strip()) for item in manifest["keywords"])
    edition = contest_edition(contest_config)
    lines = [
        "% !TEX program = xelatex",
        "% Generated by tools/build_latex.py; edit chapter fragments, not Markdown.",
        rf"\def\GMCMContestEdition{{{tex_escape(edition)}}}",
        r"\documentclass[bwprint]{gmcmthesis}",
        # Keep bookmarks enabled, but use plain numeric values for the
        # subsection counters so hyperref can serialize them without the
        # class's spacing commands.
        r"\hypersetup{hidelinks}",
        r"\renewcommand{\thesubsection}{\arabic{section}.\arabic{subsection}}",
        r"\renewcommand{\thesubsubsection}{\thesubsection.\arabic{subsubsection}}",
        r"\pagestyle{plain}",
        r"\usepackage[framemethod=TikZ]{mdframed}",
        r"\usepackage{subfig}",
        r"\usepackage{siunitx}",
        r"\usepackage{colortbl}",
        r"\usepackage{array}",
        r"\usepackage{tabularx}",
        r"\usepackage{longtable}",
        r"\newcommand{\codeid}[1]{\nolinkurl{#1}}",
        r"\usepackage{booktabs}",
        r"\usepackage{tikz}",
        r"\usetikzlibrary{arrows.meta,positioning,fit,calc,shapes.geometric,shapes.arrows}",
        rf"\title{{{title}}}",
        "",
        r"\begin{document}",
        # gmcmthesis renders an anonymous abstract page, begins numbering at
        # 1, and keeps the centered footer number visible.
        r"\maketitle",
        r"\begin{abstract}",
        rf"\input{{{inputs[0]}}}",
        rf"\keywords{{{keywords}}}",
        r"\end{abstract}",
    ]
    appendix_started = False
    for chapter, input_path in zip(manifest["chapters"], inputs[1:], strict=True):
        if chapter["role"] in {"references", "appendix"}:
            lines.append(r"\clearpage")
        if chapter["role"] == "appendix" and not appendix_started:
            lines.append(r"\appendix")
            appendix_started = True
        lines.append(rf"\input{{{input_path}}}")
    lines.extend([r"\end{document}", ""])
    return "\n".join(lines), inputs


def copy_assets(template_dir: Path, output_dir: Path) -> None:
    for name in ("gmcmthesis.cls", "gmcm.bst", "reference.bib", "gmcm-title.sty"):
        source = template_dir / name
        if source.is_file():
            shutil.copy2(source, output_dir / name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--template-dir", type=Path, required=True)
    parser.add_argument("--manifest-out", type=Path)
    parser.add_argument("--contest-config", type=Path, help="根目录比赛配置.json；省略时自动向上查找")
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    root = manifest_path.parent
    manifest = load_manifest(manifest_path)
    contest_config = load_contest_config(root, args.contest_config)
    main_text, inputs = build_main(manifest, root, contest_config)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    copy_assets(args.template_dir.resolve(), output.parent)
    output.write_text(main_text, encoding="utf-8")
    out_manifest = args.manifest_out.resolve() if args.manifest_out else output.with_suffix(".inputs.json")
    out_manifest.write_text(json.dumps({"main": output.name, "inputs": inputs, "title": manifest["title"], "contest_edition_cn": contest_edition(contest_config)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "inputs": inputs, "manifest": str(out_manifest)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
