#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_论文规范模板/tools/，相对路径已改为 CLI 参数驱动，Wave3 验证编译链路。
r"""Audit the TeX-only paper source and its generated ``\input`` chain."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^{}]+)\}")
GRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^]]*\])?\s*\{([^{}]+)\}")
BEGIN_RE = re.compile(r"\\begin\s*\{([^{}]+)\}")
END_RE = re.compile(r"\\end\s*\{([^{}]+)\}")
LABEL_RE = re.compile(r"\\label\s*\{([^{}]+)\}")
REF_RE = re.compile(r"\\(?:ref|eqref|autoref|pageref)\s*\{([^{}]+)\}")
FORBIDDEN_UNICODE_MATH = set("ᐟ¹²³⁴⁵⁶⁷⁸⁹⁰⁻⁺Σ∑∫√∈∉≤≥≈μσπγδελρτφω̃ᵀĉŷ")
GRAPHIC_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".eps")
DANGEROUS_ANYWHERE_RE = re.compile(
    r"\\(?:write18|openin|openout|read|newread|newwrite|catcode)\b",
    re.IGNORECASE,
)
DANGEROUS_FRAGMENT_RE = re.compile(
    r"\\(?:usepackage|documentclass|includeonly|subfile|import|subimport|"
    r"includefrom|inputfrom|includepdf|lstinputlisting|verbatiminput|"
    r"inputminted|bibliography|addbibresource)\b",
    re.IGNORECASE,
)


def read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def decode_tex_path(raw: str) -> str:
    clean = raw.strip()
    for escaped, literal in ((r"\ ", " "), (r"\#", "#"), (r"\%", "%"), (r"\&", "&")):
        clean = clean.replace(escaped, literal)
    return clean


def inside(root: Path, raw: str) -> Path:
    clean = decode_tex_path(raw)
    path = (root / clean).resolve()
    path.relative_to(root.resolve())
    return path


def remove_comments(text: str) -> str:
    cleaned = []
    for line in text.splitlines():
        cut = len(line)
        for index, char in enumerate(line):
            if char != "%":
                continue
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                cut = index
                break
        cleaned.append(line[:cut])
    return "\n".join(cleaned)


def find_project_root(paper_root: Path) -> Path:
    """Use the nearest contest config as the file-access boundary."""
    for candidate in (paper_root.resolve(), *paper_root.resolve().parents):
        if (candidate / "比赛配置.json").is_file():
            return candidate
    return paper_root.resolve()


def collect_fragment_chain(initial: list[Path], root: Path) -> tuple[list[Path], list[str]]:
    r"""Collect static local ``\input`` files and reject cycles/dynamic inputs."""
    collected: list[Path] = []
    visited: set[Path] = set()
    active: set[Path] = set()
    errors: list[str] = []

    def visit(path: Path) -> None:
        resolved = path.resolve()
        if resolved in active:
            errors.append(f"TeX input cycle: {resolved}")
            return
        if resolved in visited:
            return
        visited.add(resolved)
        active.add(resolved)
        collected.append(resolved)
        cleaned = remove_comments(resolved.read_text(encoding="utf-8-sig"))
        inputs = INPUT_RE.findall(cleaned)
        if len(re.findall(r"\\(?:input|include)\b", cleaned)) != len(inputs):
            errors.append(f"dynamic or malformed \\input/\\include is not allowed: {resolved}")
        for raw in inputs:
            candidate = raw if raw.lower().endswith(".tex") else raw + ".tex"
            try:
                child = inside(root, candidate)
            except (ValueError, OSError) as exc:
                errors.append(f"{resolved}: {raw}: {exc}")
                continue
            if not child.is_file():
                errors.append(f"{resolved}: nested input does not exist: {raw}")
                continue
            visit(child)
        active.remove(resolved)

    for path in initial:
        visit(path)
    return collected, errors


def strip_identity_cover_commands(text: str) -> str:
    """Remove the one officially permitted identity zone from TeX text."""
    clean = text
    for command in ("schoolname", "baominghao", "membera", "memberb", "memberc"):
        clean = re.sub(rf"\\{command}\s*\{{[^{{}}]*\}}", "", clean, flags=re.S)
    return re.sub(r"\\makeidentitycover\b", "", clean)


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
    project_root = find_project_root(root)
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

    # Attachment 2 states that the page after the complete abstract begins
    # the body.  A generated table of contents between them is non-compliant.
    clean_main = remove_comments(main_text)
    abstract_end = clean_main.find(r"\end{abstract}")
    after_abstract = clean_main[abstract_end + len(r"\end{abstract}"):] if abstract_end >= 0 else ""
    first_input_match = re.search(r"\\input\s*\{", after_abstract)
    first_input_pos = abstract_end + len(r"\end{abstract}") + first_input_match.start() if abstract_end >= 0 and first_input_match else -1
    toc_commands = re.findall(r"\\(?:maketoc|tableofcontents)\b", clean_main)
    add("no_toc_in_official_submission", not toc_commands, commands=toc_commands,
        message="官方规定：完整摘要后的下一页直接开始正文。")
    between = after_abstract[:first_input_match.start()] if first_input_match else ""
    only_page_breaks = re.sub(r"\\(?:clearpage|newpage)\b", "", between).strip()
    add("body_follows_complete_abstract", abstract_end >= 0 and first_input_pos >= 0 and not only_page_breaks,
        abstract_end=abstract_end, first_body_input=first_input_pos, intervening=between.strip())
    add("main_does_not_override_official_geometry", not re.search(r"\\geometry\s*\{", clean_main),
        message="页边距由 gmcmthesis.cls 统一设为官方 Word 模板的 30/17.5/22.5/22.5 mm。")
    cover_pos = clean_main.find(r"\makeidentitycover")
    title_pos = clean_main.find(r"\maketitle")
    cover_fields = {
        command: bool(re.search(rf"\\{command}\s*\{{", clean_main))
        for command in ("schoolname", "baominghao", "membera", "memberb", "memberc")
    }
    add(
        "uses_required_identity_cover",
        cover_pos >= 0 and title_pos > cover_pos and all(cover_fields.values()),
        fields=cover_fields,
        message="2026 正式提交：先输出第 0 页封皮，再输出页码 1 的匿名摘要页。",
    )
    add("plain_page_style", bool(re.search(r"\\pagestyle\s*\{plain\}", clean_main)),
        message="plain 页式确保无页眉、页脚居中阿拉伯页码。")

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
    fragment_paths, nested_input_errors = collect_fragment_chain(fragment_paths, root)
    add("nested_inputs_are_static_and_local", not nested_input_errors, errors=nested_input_errors)

    markdown_residue: list[str] = []
    document_commands: list[str] = []
    unbalanced: list[str] = []
    environment_errors: list[str] = []
    main_cleaned = strip_identity_cover_commands(remove_comments(main_text))
    dangerous_commands = [
        f"{main_path}: {match.group(0)}"
        for match in DANGEROUS_ANYWHERE_RE.finditer(main_cleaned)
    ]
    all_text = main_cleaned
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
        dangerous_commands.extend(
            f"{path}: {match.group(0)}"
            for regex in (DANGEROUS_ANYWHERE_RE, DANGEROUS_FRAGMENT_RE)
            for match in regex.finditer(cleaned)
        )
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
    dangerous_commands = sorted(set(dangerous_commands))
    add("no_dangerous_tex_file_or_shell_commands", not dangerous_commands, commands=dangerous_commands)

    missing_graphics: list[str] = []
    for raw in GRAPHICS_RE.findall(all_text):
        try:
            # The paper source may reference real result figures stored in
            # the sibling 求解/ tree.  Inputs remain confined to 论文/;
            # graphics are allowed anywhere inside the project root.
            path = (root / decode_tex_path(raw)).resolve()
            path.relative_to(project_root.resolve())
        except (ValueError, OSError):
            missing_graphics.append(raw)
            continue
        candidates = [path] if path.suffix else [path.with_suffix(ext) for ext in GRAPHIC_EXTENSIONS]
        if not any(candidate.is_file() for candidate in candidates):
            missing_graphics.append(raw)
    add("graphics_paths_exist", not missing_graphics, missing=missing_graphics)

    identity_hits = sorted(set(re.findall(
        r"(?:学校|学院|实验室|参赛队号|队员姓名|指导教师|学号|邮箱)\s*[:：]|"
        r"\\(?:schoolname|baominghao|member[abc]|makeidentitycover)\b|C:\\Users\\",
        all_text,
        re.I,
    )))
    add("anonymous_source_after_cover", not identity_hits, matches=identity_hits)
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
