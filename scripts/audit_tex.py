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
CODE_BLOCK_RE = re.compile(
    r"\\begin\s*\{(?P<env>Python|Matlab|lstlisting|algorithm|algorithmic|verbatim)\}"
    r"(?P<body>.*?)\\end\s*\{(?P=env)\}",
    re.IGNORECASE | re.DOTALL,
)
PSEUDOCODE_SEMANTICS = {
    "input": re.compile(r"\b(?:input|load|read|data|dataset|manifest)\b|输入|读取|载入|数据", re.IGNORECASE),
    "config": re.compile(
        r"\b(?:seed|config|parameter|tolerance|random_state)\b|随机种子|配置|参数|容差",
        re.IGNORECASE,
    ),
    "compute": re.compile(
        r"\b(?:fit|train|solve|optimi[sz]\w*|calibrat\w*|predict\w*|estimate\w*)\b|"
        r"拟合|训练|求解|优化|校准|预测|估计",
        re.IGNORECASE,
    ),
    "validate": re.compile(
        r"\b(?:evaluate|metric|check|bootstrap|validate|test)\w*\b|评估|指标|检验|验证|测试",
        re.IGNORECASE,
    ),
    "export": re.compile(
        r"\b(?:export|save|write|dump|output)\w*\b|导出|保存|写出|输出|结果文件",
        re.IGNORECASE,
    ),
}
SOURCE_ANCHOR_RE = re.compile(r"[\w./\\-]+\.(?:py|m|r|jl|ipynb)\b", re.IGNORECASE)
RESULT_ANCHOR_RE = re.compile(
    r"[\w./\\-]+\.(?:csv|json|xlsx|mat|joblib|npz|parquet)\b",
    re.IGNORECASE,
)
PLACEHOLDER_LINE_RE = re.compile(
    r"(?im)^\s*(?:pass|\.\.\.|(?:\#|%)?\s*(?:TODO|FIXME|TBD)\b.*)\s*$"
)
GENERIC_PLACEHOLDER_CALL_RE = re.compile(
    r"\b(?P<name>audit_and_clean|build_features|solve_model)\s*\(",
    re.IGNORECASE,
)
PYTHON_FUNCTION_DEF_RE = re.compile(
    r"(?im)^\s*def\s+(?P<name>[A-Za-z_]\w*)\s*\("
)
MATLAB_FUNCTION_DEF_RE = re.compile(
    r"(?im)^\s*function\s+(?:(?:\[[^\]]+\]|[A-Za-z_]\w*)\s*=\s*)?"
    r"(?P<name>[A-Za-z_]\w*)\s*\("
)
TEMPLATE_SENTINEL_RE = re.compile(r"REPLACE_WITH_ACTUAL(?:_[A-Z0-9_]+)?", re.IGNORECASE)
QUESTION_SECTION_RE = re.compile(
    r"\\section\*?(?:\[[^]]*\])?\s*\{(?P<title>\s*(?:"
    r"问题\s*(?:[一二三四五六七八九十百]+|\d+)|"
    r"第\s*(?:[一二三四五六七八九十百]+|\d+)\s*问|"
    r"Q\s*\d+|Question\s*\d+"
    r")[^{}]*)\}",
    re.IGNORECASE,
)
ANY_SECTION_RE = re.compile(r"\\section\*?(?:\[[^]]*\])?\s*\{")
QUESTION_OPENER_BOUNDARY_RE = re.compile(
    r"\\(?:subsection|subsubsection)\*?(?:\[[^]]*\])?\s*\{|"
    r"\\begin\s*\{(?:equation\*?|align\*?|gather\*?|multline\*?|"
    r"table\*?|figure\*?|algorithm|algorithmic|lstlisting|Python|Matlab)\}|"
    r"\\(?:includegraphics|evidencefigure|frameworkfigure|roadmapfigure)\b|\\\[",
    re.IGNORECASE,
)
QUESTION_OPENER_SEMANTICS = {
    "problem_recap": re.compile(
        r"本问|题目|问题\s*(?:[一二三四五六七八九十百]+|\d+)|"
        r"第\s*(?:[一二三四五六七八九十百]+|\d+)\s*问|Q\s*\d+|Question\s*\d+|承接|"
        r"在.{0,24}基础上|给定|围绕|需要|目标",
        re.IGNORECASE,
    ),
    "method_route": re.compile(
        r"采用|使用|通过|基于|先|随后|再|然后|方法|模型|算法|"
        r"估计|求解|比较|校准|检验|分析",
        re.IGNORECASE,
    ),
    "method_reason": re.compile(
        r"因为|由于|针对|考虑到|鉴于|为避免|为区分|为分开|为分别处理|"
        r"为解决|以免|不.{0,20}而是|从而避免",
        re.IGNORECASE,
    ),
    "deliverable": re.compile(
        r"得到|给出|输出|回答|确定|量化|形成|评价|结论|结果|"
        r"传递|支撑|提供",
        re.IGNORECASE,
    ),
}
QUESTION_OPENER_SENTINEL_RE = re.compile(
    r"REPLACE_WITH_ACTUAL_QUESTION_(?:GUIDE|OPENER)", re.IGNORECASE
)
QUESTION_OPENER_GENERIC_RE = re.compile(
    r"本问|本节|本部分|问题|题目|提出|主要|针对|开展|进行|分析|研究|"
    r"目标|相关|内容|为此|首先|先|然后|随后|再|最后|采用|使用|通过|"
    r"基于|合适|合理|模型|方法|算法|完成|求解|得到|给出|形成|相应|"
    r"结果|结论|后续|提供|依据|需要|将|可以|从而|以及|其中|"
    r"[的地得和与及在对把由为中上下一二三四五六七八九十]",
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


def expand_tex_in_order(path: Path, root: Path, active: set[Path] | None = None) -> tuple[str, list[str]]:
    r"""Expand static local ``\input`` files at their source position for prose-order checks."""
    active = set() if active is None else set(active)
    resolved = path.resolve()
    if resolved in active:
        return "", [f"TeX input cycle: {resolved}"]
    active.add(resolved)
    cleaned = remove_comments(resolved.read_text(encoding="utf-8-sig"))
    errors: list[str] = []
    matches = list(INPUT_RE.finditer(cleaned))
    if len(re.findall(r"\\(?:input|include)\b", cleaned)) != len(matches):
        errors.append(f"dynamic or malformed \\input/\\include is not allowed: {resolved}")
    pieces: list[str] = []
    cursor = 0
    for match in matches:
        pieces.append(cleaned[cursor:match.start()])
        raw = match.group(1)
        candidate = raw if raw.lower().endswith(".tex") else raw + ".tex"
        try:
            child = inside(root, candidate)
        except (ValueError, OSError) as exc:
            errors.append(f"{resolved}: {raw}: {exc}")
            cursor = match.end()
            continue
        if not child.is_file():
            errors.append(f"{resolved}: nested input does not exist: {raw}")
            cursor = match.end()
            continue
        child_text, child_errors = expand_tex_in_order(child, root, active)
        pieces.append(child_text)
        errors.extend(child_errors)
        cursor = match.end()
    pieces.append(cleaned[cursor:])
    return "\n".join(pieces), errors


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


def audit_question_openers(text: str) -> list[dict]:
    """Check that numbered problem sections orient the reader before technical detail."""
    cleaned = remove_comments(text)
    appendix_pos = cleaned.find(r"\appendix")
    if appendix_pos >= 0:
        cleaned = cleaned[:appendix_pos]
    section_starts = [match.start() for match in ANY_SECTION_RE.finditer(cleaned)]
    findings: list[dict] = []
    for match in QUESTION_SECTION_RE.finditer(cleaned):
        section_end = next(
            (position for position in section_starts if position > match.start()),
            len(cleaned),
        )
        body = cleaned[match.end():section_end]
        boundary = QUESTION_OPENER_BOUNDARY_RE.search(body)
        opener_tex = body[:boundary.start()] if boundary else body
        opener_tex = re.sub(r"\\label\s*\{[^{}]*\}", " ", opener_tex)
        opener_text = re.sub(r"\\(?:ref|eqref|autoref|pageref|cite)\s*\{[^{}]*\}", " ", opener_tex)
        opener_text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^]]*\])?", " ", opener_text)
        opener_text = re.sub(r"[{}$~^_\\]", " ", opener_text)
        opener_text = re.sub(r"\s+", " ", opener_text).strip()
        visible_chars = len(re.sub(r"\s+", "", opener_text))
        sentence_count = len(re.findall(r"[。！？；]", opener_text))
        semantics = {
            name: bool(pattern.search(opener_text))
            for name, pattern in QUESTION_OPENER_SEMANTICS.items()
        }
        has_sentinel = bool(QUESTION_OPENER_SENTINEL_RE.search(opener_tex))
        specific_text = QUESTION_OPENER_GENERIC_RE.sub("", opener_text)
        specific_chars = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", specific_text))
        generic_only = specific_chars < 12
        ok = (
            visible_chars >= 60
            and sentence_count >= 2
            and all(semantics.values())
            and not generic_only
            and not has_sentinel
        )
        findings.append({
            "title": re.sub(r"\s+", " ", match.group("title")).strip(),
            "ok": ok,
            "visible_chars": visible_chars,
            "sentence_count": sentence_count,
            "semantics": semantics,
            "specific_chars_after_generic_words": specific_chars,
            "generic_only": generic_only,
            "placeholder": has_sentinel,
            "preview": opener_text[:160],
        })
    return findings


def unresolved_generic_placeholder_calls(code: str, appendix_text: str) -> list[str]:
    """Find generic template calls without a concrete implementation anchor.

    A project may legitimately use one of the otherwise-generic names.  It is
    accepted only when the appendix either defines that function in the shown
    code or maps it explicitly as ``script.py::function_name`` (``#`` is also
    accepted as a source-location separator).  Merely mentioning ``solve.py``
    elsewhere is not a function-level mapping and must not make a template
    chain pass.
    """
    calls = {
        match.group("name").lower()
        for match in GENERIC_PLACEHOLDER_CALL_RE.finditer(code)
    }
    if not calls:
        return []

    definitions = {
        match.group("name").lower()
        for pattern in (PYTHON_FUNCTION_DEF_RE, MATLAB_FUNCTION_DEF_RE)
        for match in pattern.finditer(code)
    }
    mapped: set[str] = set()
    for name in calls:
        explicit_mapping = re.compile(
            rf"[\w./\\-]+\.(?:py|m|r|jl|ipynb)\s*(?:::|#)\s*{re.escape(name)}\b",
            re.IGNORECASE,
        )
        if explicit_mapping.search(appendix_text):
            mapped.add(name)
    return sorted(calls - definitions - mapped)


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
    clean_main = remove_comments(main_text)
    input_matches = list(INPUT_RE.finditer(clean_main))
    actual = [match.group(1) for match in input_matches]
    add("input_order_matches_manifest", actual == expected, expected=expected, actual=actual)
    add("main_has_no_markdown_input", not any(path.lower().endswith(".md") for path in actual), actual=actual)

    terminal_page_starts = []
    for chapter in manifest.get("chapters", []):
        role = str(chapter.get("role", "")).strip()
        if role not in {"references", "appendix"}:
            continue
        target = str(chapter.get("tex_path", "")).replace("\\", "/")
        match_index = next(
            (index for index, match in enumerate(input_matches)
             if match.group(1).replace("\\", "/") == target),
            None,
        )
        between = ""
        if match_index is not None:
            previous_end = input_matches[match_index - 1].end() if match_index > 0 else 0
            between = clean_main[previous_end:input_matches[match_index].start()]
        terminal_page_starts.append({
            "chapter_id": chapter.get("chapter_id"),
            "role": role,
            "tex_path": target,
            "has_clearpage": bool(re.search(r"\\clearpage\b", between)),
        })
    add(
        "references_and_appendices_start_new_pages",
        all(item["has_clearpage"] for item in terminal_page_starts),
        chapters=terminal_page_starts,
        message="参考文献与每个附录入口前必须用 \\clearpage 清空浮动体并另起一页。",
    )

    # Attachment 2 states that the page after the complete abstract begins
    # the body.  A generated table of contents between them is non-compliant.
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

    appendix_roots: list[Path] = []
    appendix_path_errors: list[str] = []
    for chapter in manifest.get("chapters", []):
        if str(chapter.get("role", "")).strip() != "appendix":
            continue
        raw = str(chapter.get("tex_path", ""))
        try:
            path = inside(root, raw)
        except (ValueError, OSError) as exc:
            appendix_path_errors.append(f"{raw}: {exc}")
            continue
        if path.is_file() and path.suffix.lower() == ".tex":
            appendix_roots.append(path)
        else:
            appendix_path_errors.append(f"{raw}: appendix source is missing or is not .tex")
    appendix_paths, appendix_nested_errors = collect_fragment_chain(appendix_roots, root)
    appendix_errors = appendix_path_errors + appendix_nested_errors
    appendix_text = "\n".join(
        remove_comments(path.read_text(encoding="utf-8-sig"))
        for path in appendix_paths
    )

    policy = manifest.get("appendix_pseudocode", {})
    policy_ok = isinstance(policy, dict)
    required_value = policy.get("required", True) if policy_ok else True
    policy_ok = policy_ok and isinstance(required_value, bool)
    reason = str(policy.get("reason", "")).strip() if isinstance(policy, dict) else ""
    if policy_ok and required_value is False:
        policy_ok = len(reason) >= 8 and not TEMPLATE_SENTINEL_RE.search(reason)
    pseudocode_required = required_value if policy_ok else True
    applicable = bool(appendix_roots) or bool(
        isinstance(policy, dict) and policy.get("required") is True
    )
    add(
        "appendix_pseudocode_policy_valid",
        not applicable or policy_ok,
        applicable=applicable,
        required=pseudocode_required,
        reason=reason,
        errors=appendix_errors,
        message="纯非计算论文可设 appendix_pseudocode.required=false，但必须给出至少 8 字的具体理由。",
    )

    code_blocks = [match.group("body") for match in CODE_BLOCK_RE.finditer(appendix_text)]
    has_code_block = bool(code_blocks)
    code_required_now = applicable and pseudocode_required
    add(
        "appendix_has_code_style_pseudocode",
        not code_required_now or (not appendix_errors and has_code_block),
        applicable=applicable,
        required=pseudocode_required,
        environments=[match.group("env") for match in CODE_BLOCK_RE.finditer(appendix_text)],
        message="计算型论文附录至少需要一个 Python/Matlab/lstlisting/algorithm 等代码式伪代码环境。",
    )

    pseudocode_text = "\n".join(code_blocks)
    meaningful_lines = [
        line.strip()
        for line in pseudocode_text.splitlines()
        if line.strip()
        and not line.lstrip().startswith(("#", "%"))
        and not re.fullmatch(r"\{[^{}]*\}", line.strip())
    ]
    semantic_hits = {
        name: bool(pattern.search("\n".join(meaningful_lines)))
        for name, pattern in PSEUDOCODE_SEMANTICS.items()
    }
    source_anchors = sorted(set(SOURCE_ANCHOR_RE.findall(appendix_text)))
    result_anchors = sorted(set(RESULT_ANCHOR_RE.findall(appendix_text)))
    placeholders = sorted(set(PLACEHOLDER_LINE_RE.findall(pseudocode_text)))
    sentinels = sorted(set(TEMPLATE_SENTINEL_RE.findall(pseudocode_text)))
    generic_placeholder_calls = unresolved_generic_placeholder_calls(
        pseudocode_text, appendix_text
    )
    traceable = (
        len(meaningful_lines) >= 5
        and all(semantic_hits.values())
        and bool(source_anchors)
        and bool(result_anchors)
        and not placeholders
        and not sentinels
        and not generic_placeholder_calls
    )
    add(
        "appendix_pseudocode_is_traceable",
        not code_required_now or (has_code_block and traceable),
        applicable=applicable,
        required=pseudocode_required,
        meaningful_line_count=len(meaningful_lines),
        semantics=semantic_hits,
        source_anchors=source_anchors,
        result_anchors=result_anchors,
        placeholders=placeholders,
        template_sentinels=sentinels,
        generic_placeholder_calls=generic_placeholder_calls,
        message=(
            "伪代码必须覆盖输入、配置、计算、验证、导出，并回链实际脚本和结果文件；"
            "不得保留占位行或未定义、未按 script.py::function 映射的通用空壳调用。"
        ),
    )

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

    expanded_paper, question_expansion_errors = expand_tex_in_order(main_path, root)
    question_openers = audit_question_openers(expanded_paper)
    add(
        "question_sections_open_with_recap_route_and_deliverable",
        not question_expansion_errors and all(item["ok"] for item in question_openers),
        applicable=bool(question_openers),
        sections=question_openers,
        expansion_errors=question_expansion_errors,
        message=(
            "每个编号问题须在首个小标题、公式或图表前，用至少两句实质正文完成"
            "题意/承接回溯、方法路线和结果交付定位；不得以空泛过渡或模板占位代替。"
        ),
    )

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
