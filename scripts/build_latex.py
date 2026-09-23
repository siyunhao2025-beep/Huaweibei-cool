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
import unicodedata
from pathlib import Path

from audit_tex import MANIFEST_REASON_SENTINEL_RE, question_opener_manifest_contract


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
    if not isinstance(data, dict):
        raise ValueError("manifest 必须是 JSON 对象")
    required = {"title", "keywords", "abstract_tex_path", "appendix_pseudocode", "chapters"}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"manifest 缺少字段: {', '.join(missing)}")
    forbidden = {"abstract", "content", "content_file"} & set(data)
    if forbidden:
        raise ValueError(f"LaTeX-first manifest 禁止字段: {', '.join(sorted(forbidden))}")
    if not str(data["title"]).strip():
        raise ValueError("论文题目不能为空")
    if not isinstance(data["keywords"], list) or not all(
        isinstance(item, str) for item in data["keywords"]
    ):
        raise ValueError("关键词必须是字符串数组")
    keywords = [item.strip() for item in data["keywords"]]
    if any(not item for item in keywords):
        raise ValueError("关键词不能包含空字符串")
    if not 3 <= len(keywords) <= 6:
        raise ValueError("关键词必须提供 3–6 个")
    normalized_keywords = [
        re.sub(r"\s+", "", unicodedata.normalize("NFKC", item)).casefold()
        for item in keywords
    ]
    if len(set(normalized_keywords)) != len(normalized_keywords):
        raise ValueError("关键词规范化后不得重复")
    data["keywords"] = keywords
    if not isinstance(data["chapters"], list) or not data["chapters"]:
        raise ValueError("chapters 不能为空")
    chapter_ids: set[str] = set()
    orders: list[int] = []
    for index, chapter in enumerate(data["chapters"], start=1):
        if not isinstance(chapter, dict):
            raise ValueError(f"第 {index} 个章节必须是对象")
        required_chapter = {"chapter_id", "title", "role", "order", "tex_path"}
        missing_chapter = sorted(required_chapter - set(chapter))
        if missing_chapter:
            raise ValueError(f"第 {index} 个章节缺少字段: {', '.join(missing_chapter)}")
        if chapter["role"] not in ROLES:
            raise ValueError(f"章节角色无效: {chapter['role']}")
        chapter_id = str(chapter["chapter_id"]).strip()
        if not chapter_id or chapter_id in chapter_ids:
            raise ValueError(f"chapter_id 不能为空且不得重复: {chapter_id!r}")
        chapter_ids.add(chapter_id)
        if not str(chapter["title"]).strip():
            raise ValueError(f"章节 {chapter_id} 的 title 不能为空")
        try:
            orders.append(int(chapter["order"]))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"章节 {chapter_id} 的 order 必须是整数") from exc
        if "content_file" in chapter or "content" in chapter:
            raise ValueError(f"章节 {chapter['chapter_id']} 仍使用旧 content/content_file 字段")
        if str(chapter["tex_path"]).lower().endswith(".md"):
            raise ValueError(f"章节 {chapter['chapter_id']} 禁止使用 Markdown 源文件")
    if orders != sorted(orders) or len(set(orders)) != len(orders):
        raise ValueError("章节 order 必须严格递增且不重复")
    question_contract = question_opener_manifest_contract(data)
    if not question_contract["ok"]:
        raise ValueError("question_openers 配置无效: " + "; ".join(question_contract["errors"]))
    policy = data["appendix_pseudocode"]
    if not isinstance(policy, dict) or set(policy) - {"required", "reason"}:
        raise ValueError("appendix_pseudocode 必须是仅含 required/reason 的对象")
    if type(policy.get("required")) is not bool:
        raise ValueError("appendix_pseudocode.required 必须显式为布尔值")
    if "reason" in policy and not isinstance(policy["reason"], str):
        raise ValueError("appendix_pseudocode.reason 必须是字符串")
    if policy["required"] is False:
        reason = str(policy.get("reason", "")).strip()
        if len(reason) < 8 or MANIFEST_REASON_SENTINEL_RE.search(reason) or not re.search(
            r"纯解析|解析推导|理论推导|闭式|证明|不依赖|不涉及|无需|未使用|没有使用|"
            r"analytic|closed[- ]form|proof|without|does not",
            reason,
            re.IGNORECASE,
        ):
            raise ValueError("appendix_pseudocode.required=false 必须给出充分具体的不适用理由")
    if policy["required"] is True and not any(
        chapter["role"] == "appendix" for chapter in data["chapters"]
    ):
        raise ValueError("appendix_pseudocode.required=true 时必须声明 appendix 章节")
    return data


def check_fragment(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError(f"章节 fragment 不能为空: {path}")
    if "\\documentclass" in text or "\\begin{document}" in text or "\\end{document}" in text:
        raise ValueError(f"章节 fragment 不得包含 document 级结构: {path}")
    if re.search(r"(?m)^\s*#{1,6}\s", text) or re.search(r"(?m)^\s*\|[^|]+\|", text) or "![" in text:
        raise ValueError(f"章节 fragment 残留 Markdown 语法: {path}")


def build_main(manifest: dict, root: Path, contest_config: dict) -> tuple[str, list[str]]:
    abstract = relative_file(root, manifest["abstract_tex_path"], label="abstract_tex_path")
    check_fragment(abstract)
    inputs = [abstract.relative_to(root).as_posix()]
    for chapter in manifest["chapters"]:
        fragment = relative_file(root, str(chapter["tex_path"]), label=f"章节 {chapter['chapter_id']}")
        check_fragment(fragment)
        inputs.append(fragment.relative_to(root).as_posix())

    raw_title = str(manifest["title"]).strip()
    title = tex_escape(raw_title)
    keywords = r"\quad ".join(
        rf"\mbox{{{tex_escape(str(item).strip())}}}" for item in manifest["keywords"]
    )
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
        r"% 2026 正式提交必须填写以下封皮字段。",
        r"\schoolname{}",
        r"\baominghao{}",
        r"\membera{}",
        r"\memberb{}",
        r"\memberc{}",
        "",
        r"\begin{document}",
        # Physical page 1 is the required identity cover (printed page 0).
        # The abstract/body remain anonymous and restart at printed page 1.
        r"\makeidentitycover",
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
    root_assets = ("gmcmthesis.cls", "gmcm.bst", "reference.bib", "gmcm-title.sty")
    figure_assets = (
        "identity-cpipc.png",
        "identity-gmcm.png",
        "identity-huawei.jpg",
        "identity-xjtu.png",
    )
    missing = [str(template_dir / name) for name in root_assets if not (template_dir / name).is_file()]
    missing.extend(
        str(template_dir / "figures" / name)
        for name in figure_assets
        if not (template_dir / "figures" / name).is_file()
    )
    if missing:
        raise FileNotFoundError("LaTeX 模板资产不完整:\n- " + "\n- ".join(missing))

    for name in root_assets:
        source = template_dir / name
        destination = output_dir / name
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
    figure_output = output_dir / "figures"
    figure_output.mkdir(parents=True, exist_ok=True)
    for name in figure_assets:
        source = template_dir / "figures" / name
        destination = figure_output / name
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)


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
    template_dir = args.template_dir.resolve()
    if output.suffix.lower() != ".tex":
        raise ValueError(f"主文件输出必须是 .tex: {output}")
    try:
        output.relative_to(template_dir)
    except ValueError:
        pass
    else:
        raise ValueError("不得把主文件写进模板源目录")
    protected_inputs = {manifest_path}
    protected_inputs.update((root / raw).resolve() for raw in inputs)
    if output in protected_inputs:
        raise ValueError(f"输出不得覆盖 manifest 或章节源文件: {output}")
    out_manifest = args.manifest_out.resolve() if args.manifest_out else output.with_suffix(".inputs.json")
    if out_manifest.suffix.lower() != ".json":
        raise ValueError(f"构建清单必须是 .json: {out_manifest}")
    if args.contest_config:
        protected_inputs.add(args.contest_config.resolve())
    if out_manifest == output or out_manifest in protected_inputs:
        raise ValueError(f"构建清单不得覆盖论文源文件: {out_manifest}")
    output.parent.mkdir(parents=True, exist_ok=True)
    copy_assets(template_dir, output.parent)
    output.write_text(main_text, encoding="utf-8")
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps({"main": output.name, "inputs": inputs, "title": manifest["title"], "contest_edition_cn": contest_edition(contest_config)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "inputs": inputs, "manifest": str(out_manifest)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
