#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_论文规范模板/tools/，相对路径已改为 CLI 参数驱动，Wave3 验证编译链路。
"""Audit the TeX-only paper source and its generated ``\input`` chain."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


INPUT_RE = re.compile(r"\\input\s*\{([^{}]+)\}")
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^]]*\])?\s*\{([^{}]+)\}")
BEGIN_RE = re.compile(r"\\begin\s*\{([^{}]+)\}")
END_RE = re.compile(r"\\end\s*\{([^{}]+)\}")
LABEL_RE = re.compile(r"\\label\s*\{([^{}]+)\}")
REF_RE = re.compile(r"\\(?:ref|eqref|autoref|pageref)\s*\{([^{}]+)\}")
TOC_DEPTH_RE = re.compile(r"\\setcounter\s*\{tocdepth\}\s*\{\s*(\d+)\s*\}")
FORBIDDEN_UNICODE_MATH = set("ᐟ¹²³⁴⁵⁶⁷⁸⁹⁰⁻⁺Σ∑∫√∈∉≤≥≈μσπγδελρτφω̃ᵀĉŷ")


def read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def inside(root: Path, raw: str) -> Path:
    path = (root / raw).resolve()
    path.relative_to(root.resolve())
    return path


def remove_comments(text: str) -> str:
    return "\n".join(line.split("%", 1)[0] for line in text.splitlines())


def brace_balance(text: str) -> int:
    balance = 0
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "{":
            balance += 1
        elif char == "}":
            balance -= 1
    return balance


def audit(manifest_path: Path, main_path: Path) -> dict:
    root = manifest_path.parent.resolve()
    project_root = root.parent
    manifest = read_manifest(manifest_path)
    checks: list[dict] = []
    failures: list[dict] = []

    def add(code: str, ok: bool, **details) -> None:
        item = {"code": code, "ok": ok, **details}
        checks.append(item)
        if not ok:
            failures.append(item)

    main_text = main_path.read_text(encoding="utf-8-sig") if main_path.is_file() else ""
    add("main_exists", main_path.is_file(), path=str(main_path))
    if not main_path.is_file():
        return {"status": "FAIL", "manifest": str(manifest_path), "checks": checks, "failures": failures}

    expected = [str(manifest["abstract_tex_path"]).replace("\\", "/")]
    for chapter in manifest.get("chapters", []):
        expected.append(str(chapter["tex_path"]).replace("\\", "/"))
    actual = INPUT_RE.findall(remove_comments(main_text))
    add("input_order_matches_manifest", actual == expected, expected=expected, actual=actual)
    add("main_has_no_markdown_input", not any(path.lower().endswith(".md") for path in actual), actual=actual)

    # The TOC is a production contract: it must follow the complete
    # abstract/keywords block and precede the first body input.
    clean_main = remove_comments(main_text)
    toc_match = re.search(r"\\maketoc\b", clean_main)
    abstract_end = clean_main.find(r"\end{abstract}")
    after_abstract = clean_main[abstract_end + len(r"\end{abstract}"):] if abstract_end >= 0 else ""
    first_input_match = re.search(r"\\input\s*\{", after_abstract)
    first_input_pos = abstract_end + len(r"\end{abstract}") + first_input_match.start() if abstract_end >= 0 and first_input_match else -1
    toc_order_ok = bool(toc_match and abstract_end >= 0 and first_input_pos >= 0 and abstract_end < toc_match.start() < first_input_pos)
    add("toc_command_order", toc_order_ok, maketoc_position=toc_match.start() if toc_match else None,
        abstract_end=abstract_end, first_body_input=first_input_pos)
    depth_values = [int(value) for value in TOC_DEPTH_RE.findall(clean_main)]
    add("toc_depth_is_three", depth_values == [3], values=depth_values)
    add("toc_hyperlinks_enabled", bool(re.search(r"\\hypersetup\s*\{[^}]*hidelinks", clean_main, re.S)),
        message="hyperref is configured for linked TOC/bookmarks")

    fragment_paths: list[Path] = []
    fragment_errors: list[str] = []
    for raw in expected:
        try:
            path = inside(root, raw)
        except (ValueError, OSError) as exc:
            fragment_errors.append(f"{raw}: {exc}")
            continue
        if path.suffix.lower() != ".tex":
            fragment_errors.append(f"{raw}: suffix is not .tex")
        elif not path.is_file():
            fragment_errors.append(f"{raw}: file does not exist")
        else:
            fragment_paths.append(path)
    add("all_manifest_fragments_exist_and_are_tex", not fragment_errors, errors=fragment_errors)

    markdown_residue: list[str] = []
    document_commands: list[str] = []
    unbalanced: list[str] = []
    environment_errors: list[str] = []
    all_text = main_text
    for path in fragment_paths:
        text = path.read_text(encoding="utf-8-sig")
        all_text += "\n" + text
        if re.search(r"(?m)^\s*#{1,6}\s", text) or re.search(r"(?m)^\s*\|[^|]+\|", text) or "![" in text or chr(96) * 3 in text:
            markdown_residue.append(str(path))
        for command in ("\\documentclass", "\\begin{document}", "\\end{document}"):
            if command in text:
                document_commands.append(f"{path}: {command}")
        if brace_balance(remove_comments(text)) != 0:
            unbalanced.append(str(path))
        stack: list[str] = []
        cleaned = remove_comments(text)
        for match in re.finditer(r"\\begin\s*\{([^{}]+)\}|\\end\s*\{([^{}]+)\}", cleaned):
            begin, end = match.groups()
            if begin:
                stack.append(begin)
            elif not stack or stack.pop() != end:
                environment_errors.append(f"{path}: mismatched \\end{{{end}}}")
        environment_errors.extend(f"{path}: unclosed {env}" for env in stack)
    add("fragments_are_real_latex", not markdown_residue and not document_commands, markdown_residue=markdown_residue, document_commands=document_commands)
    add("fragment_braces_balanced", not unbalanced, files=unbalanced)
    add("fragment_environments_balanced", not environment_errors, errors=environment_errors)

    # After XeLaTeX, inspect the generated auxiliary file when it exists.  A
    # pre-compilation audit remains useful and reports this check as pending
    # rather than manufacturing a failure from a missing build artifact.
    toc_path = main_path.with_suffix(".toc")
    if toc_path.is_file():
        toc_text = toc_path.read_text(encoding="utf-8", errors="replace")
        toc_levels = {
            level: bool(re.search(rf"\\contentsline\s*\{{{level}\}}", toc_text))
            for level in ("section", "subsection", "subsubsection")
        }
        expected_levels = {
            level: bool(re.search(rf"\\{level}\*?\s*(?:\[[^]]*\])?\s*\{{", remove_comments(all_text)))
            for level in toc_levels
        }
        toc_content_ok = all((not expected_levels[level]) or toc_levels[level] for level in toc_levels)
        add("toc_auxiliary_content", toc_content_ok, path=str(toc_path), expected=expected_levels, found=toc_levels)
    else:
        add("toc_auxiliary_content", True, available=False, path=str(toc_path),
            message=".toc not present; run XeLaTeX before auxiliary-content validation")

    missing_graphics: list[str] = []
    for raw in GRAPHICS_RE.findall(all_text):
        try:
            # The paper source may reference real result figures stored in
            # the sibling 求解/ tree.  Inputs remain confined to 论文/;
            # graphics are allowed anywhere inside the project root.
            path = (root / raw).resolve()
            path.relative_to(project_root.resolve())
        except (ValueError, OSError):
            missing_graphics.append(raw)
            continue
        if not path.is_file():
            missing_graphics.append(raw)
    add("graphics_paths_exist", not missing_graphics, missing=missing_graphics)

    identity_hits = sorted(set(re.findall(r"学校|学院|实验室|参赛队号|队员姓名|指导教师|学号|邮箱|C:\\Users\\", all_text, re.I)))
    add("anonymous_source", not identity_hits, matches=identity_hits)
    add("no_markdown_chapter_sources", not any(path.suffix.lower() == ".md" for path in fragment_paths), files=[str(path) for path in fragment_paths if path.suffix.lower() == ".md"])

    labels = LABEL_RE.findall(remove_comments(all_text))
    duplicate_labels = sorted({label for label in labels if labels.count(label) > 1})
    references = REF_RE.findall(remove_comments(all_text))
    missing_labels = sorted(set(references) - set(labels))
    add("labels_are_unique", not duplicate_labels, duplicates=duplicate_labels)
    add("references_resolve", not missing_labels, missing=missing_labels)

    unicode_math_hits = sorted(set(all_text) & FORBIDDEN_UNICODE_MATH)
    add(
        "math_uses_latex_commands",
        not unicode_math_hits,
        characters=unicode_math_hits,
        message="Unicode 上下标/运算符易落入西文字体并造成缺字；请改用 LaTeX 数学命令。",
    )

    italic_commands = sorted(set(re.findall(r"\\(?:itshape|textit|emph)\b", remove_comments(all_text))))
    add("no_explicit_body_italic", not italic_commands, commands=italic_commands)

    return {"status": "PASS" if not failures else "FAIL", "manifest": str(manifest_path), "main": str(main_path), "checks": checks, "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.manifest.resolve(), args.main.resolve())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
