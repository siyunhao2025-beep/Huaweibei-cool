#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_论文规范模板/tools/，相对路径已改为 CLI 参数驱动，Wave3 验证编译链路。
r"""Audit the TeX-only paper source and its generated ``\input`` chain."""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
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
MANIFEST_REASON_SENTINEL_RE = re.compile(
    r"REPLACE(?:_WITH_ACTUAL(?:_[A-Z0-9_]+)?)?|\b(?:TODO|FIXME|TBD)\b|"
    r"待替换|待补|待填写|请替换|占位",
    re.IGNORECASE,
)
QUESTION_SECTION_RE = re.compile(
    r"\\section\*?(?:\[[^]]*\])?\s*\{(?P<title>\s*(?:"
    r"问题\s*(?:[一二三四五六七八九十百]+|\d+)|"
    r"第\s*(?:[一二三四五六七八九十百]+|\d+)\s*问|"
    r"Q\s*\d+|Question\s*\d+"
    r")[^{}]*)\}",
    re.IGNORECASE,
)
QUESTION_NUMBER_RE = re.compile(
    r"^\s*(?:"
    r"问题\s*(?P<problem>[零〇一二三四五六七八九十百两]+|\d+)|"
    r"第\s*(?P<ordinal>[零〇一二三四五六七八九十百两]+|\d+)\s*问|"
    r"Q\s*(?P<q>\d+)|Question\s*(?P<question>\d+)"
    r")",
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
STRUCTURAL_HEADING_RE = re.compile(
    r"\\(?P<kind>section|subsection|subsubsection)\*?"
    r"(?:\[[^]]*\])?\s*\{(?P<title>[^{}]*)\}",
    re.IGNORECASE,
)
NUMBERED_QUESTION_TITLE_RE = re.compile(
    r"^\s*(?:"
    r"问题\s*(?:[一二三四五六七八九十百]+|\d+)|"
    r"第\s*(?:[一二三四五六七八九十百]+|\d+)\s*问|"
    r"Q\s*\d+|Question\s*\d+"
    r")",
    re.IGNORECASE,
)
SYMBOL_TABLE_ENV_RE = re.compile(
    r"\\begin\s*\{(?P<env>table\*?|longtable)\}"
    r"(?P<body>.*?)"
    r"\\end\s*\{(?P=env)\}",
    re.IGNORECASE | re.DOTALL,
)
INNER_TABULAR_ENV_RE = re.compile(
    r"\\begin\s*\{(?P<env>tabularx|tabular\*?)\}"
    r"(?P<body>.*?)"
    r"\\end\s*\{(?P=env)\}",
    re.IGNORECASE | re.DOTALL,
)
DISPLAY_MATH_RE = re.compile(
    r"\\begin\s*\{(?:equation\*?|align\*?|alignat\*?|flalign\*?|gather\*?|multline\*?|cases|displaymath|eqnarray\*?)\}|"
    r"\\\[|(?<!\\)\$\$",
    re.IGNORECASE,
)
PRE_SYMBOL_TITLE_RE = re.compile(
    r"^(?:总体)?问题分析$|^数据(?:质量)?审计$|^(?:基本|模型|问题)?假设(?:说明)?$",
    re.IGNORECASE,
)
SYMBOL_PLACEHOLDER_RE = re.compile(
    r"REPLACE_WITH_ACTUAL(?:_[A-Z0-9_]+)?|"
    r"\b(?:TODO|FIXME|TBD)\b|待补|待填写|待替换|请替换|占位",
    re.IGNORECASE,
)
COVER_FIELD_NAMES = ("schoolname", "baominghao", "membera", "memberb", "memberc")
COVER_VALUE_PLACEHOLDER_RE = re.compile(
    r"REPLACE_WITH_ACTUAL(?:_[A-Z0-9_]+)?|\b(?:TODO|FIXME|TBD)\b|"
    r"待填|待补|待替换|请填写|请替换|占位",
    re.IGNORECASE,
)
ABSTRACT_LAYOUT_FORBIDDEN_RE = re.compile(
    r"\\(?:tiny|scriptsize|footnotesize|small|large|Large|LARGE|huge|Huge|"
    r"fontsize|resizebox|scalebox|linespread|setstretch|singlespacing|"
    r"onehalfspacing|doublespacing|vfill|stretch|newpage|"
    r"clearpage|pagebreak|enlargethispage|afterpage)\b|"
    r"\\(?:baselineskip|parskip)\s*=|"
    r"\\(?:hspace|vspace)\*?\s*\{\s*-|"
    r"\\(?:kern|hskip|vskip)\s*-|"
    r"\\makebox\s*\[\s*[+-]?(?:0+(?:\.0*)?|\.0+)\s*"
    r"(?:pt|bp|in|cm|mm|pc|dd|cc|sp|em|ex|\\(?:textwidth|linewidth|columnwidth))?\s*\]|"
    r"\\smash\b|"
    r"\\raisebox\s*\{\s*-",
)
PAGE_LAYOUT_OVERRIDE_RE = re.compile(
    r"\\(?:geometry|newgeometry)\s*\{|"
    r"\\(?:setlength|addtolength)\s*(?:\{\s*)?"
    r"\\(?:paperheight|paperwidth|textheight|textwidth|oddsidemargin|"
    r"evensidemargin|topmargin|headheight|headsep|footskip|marginparwidth|"
    r"marginparsep|hoffset|voffset|columnsep)\b|"
    r"\\advance\s*\\(?:paperheight|paperwidth|textheight|textwidth|"
    r"oddsidemargin|evensidemargin|topmargin|headheight|headsep|footskip|"
    r"marginparwidth|marginparsep|hoffset|voffset|columnsep)\b|"
    r"\\(?:paperheight|paperwidth|textheight|textwidth|oddsidemargin|"
    r"evensidemargin|topmargin|headheight|headsep|footskip|marginparwidth|"
    r"marginparsep|hoffset|voffset|columnsep)\s*=|"
    r"(?m:^[ \t{]*(?:\\global\s*)?"
    r"\\(?:paperheight|paperwidth|textheight|textwidth|oddsidemargin|"
    r"evensidemargin|topmargin|headheight|headsep|footskip|marginparwidth|"
    r"marginparsep|hoffset|voffset|columnsep)[ \t]+"
    r"(?=[+-]?(?:\d|\.\d|\\dimexpr\b)))",
)
LARGE_FIGURE_ENV_RE = re.compile(
    r"\\begin\s*\{(?P<env>figure\*?)\}"
    r"(?P<body>.*?)"
    r"\\end\s*\{(?P=env)\}",
    re.IGNORECASE | re.DOTALL,
)
LARGE_FIGURE_WRAPPERS = ("evidencefigure", "frameworkfigure", "roadmapfigure")
FIGURE_BRIDGE_INTERPRET_RE = re.compile(
    r"(?:图|结果|证据|分布|趋势|差异|误差|指标|关系).{0,28}"
    r"(?:显示|表明|说明|可见|揭示|反映|意味着|支持|限制|发现|观察|"
    r"给出|呈现|展开|核对|刻画|暴露|还原|明确|对照|比较|汇总|定义)|"
    r"(?:显示|表明|说明|可见|揭示|反映|给出|呈现|核对|刻画|暴露|还原|明确)"
    r".{0,28}(?:图|结果|证据|分布|趋势|差异|误差|指标|关系)",
    re.IGNORECASE | re.DOTALL,
)
FIGURE_BRIDGE_NEXT_RE = re.compile(
    r"在此基础上|基于上述|进一步|接下来|随后|下一步|下一张|下一图|下图|"
    r"为(?:进一步|检验|验证|比较|解释|刻画|分析|定位|区分|考察)|"
    r"因此.{0,24}(?:检验|验证|比较|分析|考察|转向)",
    re.IGNORECASE | re.DOTALL,
)
FIGURE_BRIDGE_CONCRETE_RE = re.compile(
    r"\d|RMSE|CSI|FAR|FSS|AUC|MAE|MSE|R2|"
    r"误差|残差|偏差|阈值|命中|虚警|时效|区间|分布|趋势|峰值|谷值|斜率|"
    r"样本|事件|参数|约束|模态|通道|变量|概率|类别|等级|区域|空间|时间|"
    r"节点|箭头|路径|模块|流程|结构|轨迹|速度|温度|成本|收益|容量|效率|"
    r"浓度|风险|覆盖|收敛|稳定|敏感|异常|边界|机制|场景|方案|曲线|离群|"
    r"增加|降低|上升|下降|高于|低于|集中|扩散|收缩|退化|改善|损失",
    re.IGNORECASE,
)
FIGURE_BRIDGE_GENERIC_RE = re.compile(
    r"上一张|上一图|下一张|下一图|下图|如图所示|图中|本图|结果|证据|"
    r"显示|表明|说明|可见|进一步|接下来|随后|下一步|在此基础上|基于上述|"
    r"为了|为此|因此|由此|进行|分析|比较|验证|检验|展示|给出|内容|情况|"
    r"[的地得和与及在对把由为中上下]",
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


def abstract_layout_violations(text: str) -> list[str]:
    """Return source-level attempts to squeeze, stretch, or paginate the abstract.

    The rendered PDF remains authoritative for the one-page span.  This helper
    only blocks common formatting tricks that could make a source check look
    compliant while silently changing the official font, leading, or page flow.
    """
    active = _active_tex_source(text)
    violations = {
        match.group(0).strip()
        for match in ABSTRACT_LAYOUT_FORBIDDEN_RE.finditer(active)
    }
    if "UNRESOLVED_TEX_CONDITIONAL" in active:
        violations.add("UNRESOLVED_TEX_CONDITIONAL")
    return sorted(violations)


def page_layout_overrides(text: str) -> list[str]:
    """Return active commands that override the template page geometry."""
    active = _active_tex_source(text)
    return sorted({
        match.group(0).strip()
        for match in PAGE_LAYOUT_OVERRIDE_RE.finditer(active)
    })


def remove_inactive_regions(text: str) -> str:
    """Remove common TeX regions that never reach the compiled document."""
    cleaned = re.sub(
        r"\\begin\s*\{comment\}.*?\\end\s*\{comment\}",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    conditional = re.compile(r"\\if[a-z@]*\b|\\else\b|\\fi\b")
    output: list[str] = []
    cursor = 0
    active = True
    frames: list[tuple[bool, bool | None]] = []
    for token in conditional.finditer(cleaned):
        command = token.group(0)
        if active:
            output.append(cleaned[cursor:token.start()])
        if command.startswith(r"\if"):
            condition = True if command == r"\iftrue" else (
                False if command == r"\iffalse" else None
            )
            parent_active = active
            frames.append((parent_active, condition))
            if parent_active and condition is None:
                output.append("\nUNRESOLVED_TEX_CONDITIONAL\n")
            active = parent_active and condition is True
        elif command == r"\else":
            if frames:
                parent_active, condition = frames[-1]
                active = parent_active and condition is False
            else:
                output.append("\nUNRESOLVED_TEX_CONDITIONAL\n")
        else:
            if frames:
                parent_active, _ = frames.pop()
                active = parent_active
            else:
                output.append("\nUNRESOLVED_TEX_CONDITIONAL\n")
        cursor = token.end()
    if active:
        output.append(cleaned[cursor:])
    if frames:
        output.append("\nUNRESOLVED_TEX_CONDITIONAL\n")
    return "".join(output)


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


def expand_tex_in_order(
    path: Path,
    root: Path,
    active: set[Path] | None = None,
    base: Path | None = None,
) -> tuple[str, list[str]]:
    r"""Expand static local ``\input`` files at their source position for prose-order checks."""
    active = set() if active is None else set(active)
    base = root.resolve() if base is None else base.resolve()
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
            child = (base / decode_tex_path(candidate)).resolve()
            child.relative_to(root.resolve())
        except (ValueError, OSError) as exc:
            errors.append(f"{resolved}: {raw}: {exc}")
            cursor = match.end()
            continue
        if not child.is_file():
            errors.append(f"{resolved}: nested input does not exist: {raw}")
            cursor = match.end()
            continue
        child_text, child_errors = expand_tex_in_order(child, root, active, base)
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


def _is_symbol_glossary_title(title: str) -> bool:
    """Return whether a heading explicitly denotes the main symbol glossary.

    A loose heading such as ``评价指标与符号`` is intentionally not enough:
    the user-confirmed paper contract requires a readily discoverable main
    symbol table, not a few definitions hidden in another subsection.
    """
    compact = re.sub(r"\s+", "", title)
    return bool(re.fullmatch(
        r"(?:\d+(?:\.\d+)*[、.]?)?(?:"
        r"主要符号(?:说明|定义|约定|表)?|全文符号(?:说明|定义|约定|表)?|"
        r"符号(?:说明|定义|约定|表)|变量(?:与|及)符号(?:说明|定义)|"
        r"符号(?:与|及)变量(?:说明|定义))",
        compact,
        re.IGNORECASE,
    ))


def _read_braced_argument(text: str, start: int) -> tuple[str | None, int]:
    """Read one balanced braced argument beginning at or after ``start``."""
    cursor = start
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor >= len(text) or text[cursor] != "{":
        return None, start
    depth = 0
    escaped = False
    for index in range(cursor, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[cursor + 1:index], index + 1
    return None, start


def _read_bracketed_argument(text: str, start: int) -> tuple[str | None, int]:
    """Read one balanced square-bracket argument beginning after ``start``."""
    cursor = start
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor >= len(text) or text[cursor] != "[":
        return None, start
    depth = 0
    escaped = False
    for index in range(cursor, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[cursor + 1:index], index + 1
    return None, start


def _caption_texts(text: str) -> list[str]:
    """Extract numbered caption bodies with balanced optional/braced arguments."""
    captions: list[str] = []
    pattern = re.compile(r"\\caption(?!\*)", re.IGNORECASE)
    for match in pattern.finditer(text):
        cursor = match.end()
        _, optional_end = _read_bracketed_argument(text, cursor)
        if optional_end != cursor:
            cursor = optional_end
        caption, _ = _read_braced_argument(text, cursor)
        if caption is not None:
            captions.append(caption.strip())
    return captions


def _balanced_macro_calls(
    text: str,
    names: tuple[str, ...],
    argument_count: int = 3,
) -> list[dict]:
    """Return ordered calls to small, fixed-arity paper macros."""
    calls: list[dict] = []
    pattern = re.compile(
        r"\\(?P<name>" + "|".join(re.escape(name) for name in names) + r")\s*\{",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        cursor = match.end() - 1
        arguments: list[str] = []
        valid = True
        for _ in range(argument_count):
            argument, end = _read_braced_argument(text, cursor)
            if argument is None:
                valid = False
                break
            arguments.append(argument)
            cursor = end
        if valid:
            calls.append({
                "name": match.group("name"),
                "args": arguments,
                "start": match.start(),
                "end": cursor,
            })
    return calls


def _mask_literal_tex_regions(text: str) -> str:
    """Mask non-executing TeX/code literals while preserving source offsets."""
    def mask(match: re.Match) -> str:
        return "".join("\n" if char == "\n" else " " for char in match.group(0))

    literal_env = re.compile(
        r"\\begin\s*\{(?P<env>verbatim\*?|lstlisting|minted|Python|Matlab)\}"
        r".*?\\end\s*\{(?P=env)\}",
        re.IGNORECASE | re.DOTALL,
    )
    masked = literal_env.sub(mask, text)
    verb = re.compile(
        r"\\(?:verb\*?|lstinline(?:\s*\[[^]]*\])?)"
        r"(?P<delimiter>[^A-Za-z0-9\s]).*?(?P=delimiter)",
        re.DOTALL,
    )
    return verb.sub(mask, masked)


def _active_tex_source(text: str) -> str:
    """Return executable TeX while ignoring literal code before parsing syntax."""
    return remove_inactive_regions(remove_comments(_mask_literal_tex_regions(text)))


def _document_body_from_active_source(cleaned: str) -> str:
    """Crop an already cleaned TeX source to its document body."""
    begin = re.search(r"\\begin\s*\{document\}", cleaned, re.IGNORECASE)
    if begin is None:
        return cleaned
    end = re.search(
        r"\\end\s*\{document\}", cleaned[begin.end():], re.IGNORECASE
    )
    if end is None:
        return cleaned[begin.end():]
    return cleaned[begin.end():begin.end() + end.start()]


def _document_body(text: str) -> str:
    """Limit prose-order checks to content that can reach the document body."""
    return _document_body_from_active_source(_active_tex_source(text))


def _figure_wrapper_specs(text: str) -> dict[str, dict]:
    """Discover local macros that directly or indirectly emit a Figure."""
    specs = {
        name.lower(): {
            "total_count": 3,
            "optional_default": None,
            "graphic_index": 0,
            "fixed_graphic": None,
            "graphic_template": "#1",
            "caption_index": 1,
            "fixed_caption": None,
            "label_index": 2,
            "fixed_label": None,
        }
        for name in LARGE_FIGURE_WRAPPERS
    }
    definitions: dict[str, tuple[int, str | None, str]] = {}
    definition_re = re.compile(
        r"\\(?:newcommand|renewcommand|providecommand)\*?\s*"
        r"(?:\{\s*\\(?P<braced_name>[A-Za-z@]+)\s*\}|"
        r"\\(?P<bare_name>[A-Za-z@]+))\s*"
        r"(?:\[(?P<count>\d+)\])?",
        re.IGNORECASE,
    )
    for match in definition_re.finditer(text):
        cursor = match.end()
        count = int(match.group("count") or 0)
        optional_default = None
        if count:
            optional_default, optional_end = _read_bracketed_argument(text, cursor)
            if optional_default is not None:
                cursor = optional_end
        body, _ = _read_braced_argument(text, cursor)
        if body is not None:
            name = match.group("braced_name") or match.group("bare_name")
            definitions[name.lower()] = (count, optional_default, body)

    xparse_re = re.compile(
        r"\\(?:NewDocumentCommand|RenewDocumentCommand|ProvideDocumentCommand)\s*"
        r"(?:\{\s*\\(?P<braced_name>[A-Za-z@]+)\s*\}|"
        r"\\(?P<bare_name>[A-Za-z@]+))",
        re.IGNORECASE,
    )
    for match in xparse_re.finditer(text):
        signature, signature_end = _read_braced_argument(text, match.end())
        if signature is None:
            continue
        body, _ = _read_braced_argument(text, signature_end)
        if body is None:
            continue
        compact = re.sub(r"\s+", "", signature)
        optional_default = None
        required_count = 0
        optional = re.fullmatch(r"O\{(?P<default>[^{}]*)\}(?P<required>m*)", compact)
        if optional:
            optional_default = optional.group("default")
            required_count = len(optional.group("required"))
        elif re.fullmatch(r"m*", compact):
            required_count = len(compact)
        else:
            continue
        name = match.group("braced_name") or match.group("bare_name")
        total_count = required_count + (optional_default is not None)
        definitions[name.lower()] = (total_count, optional_default, body)

    # A local definition is authoritative even when it reuses one of the
    # built-in wrapper names with a different arity or optional first arg.
    for name in definitions:
        specs.pop(name, None)

    changed = True
    while changed:
        changed = False
        for name, (count, optional_default, body) in definitions.items():
            if name in specs:
                continue
            direct = bool(
                re.search(r"\\begin\s*\{figure\*?\}", body, re.IGNORECASE)
                and re.search(
                    r"\\caption(?!\*)\s*(?:\[[^]]*\])?\s*\{",
                    body,
                    re.IGNORECASE,
                )
            )
            delegate_calls = [
                (call["start"], call, known_spec)
                for known, known_spec in specs.items()
                for call in _figure_wrapper_calls(body, known, known_spec)
            ]
            delegate = min(delegate_calls, default=None, key=lambda item: item[0])
            if not direct and delegate is None:
                continue
            label_match = re.search(r"\\label\s*\{\s*#(?P<index>\d+)", body)
            caption_match = re.search(
                r"\\caption(?:\[[^]]*\])?\s*\{\s*#(?P<index>\d+)", body
            )
            fixed_caption_match = re.search(
                r"\\caption(?:\[[^]]*\])?\s*\{\s*(?P<caption>[^#{}][^{}]*)\}",
                body,
            )
            graphic_template_match = re.search(
                r"\\includegraphics(?:\[[^]]*\])?\s*"
                r"\{\s*(?P<graphic>[^{}]+?)\s*\}",
                body,
                re.IGNORECASE,
            )
            graphic_template = (
                graphic_template_match.group("graphic").strip()
                if graphic_template_match else None
            )
            if graphic_template is None and delegate is not None:
                _, delegate_call, delegate_spec = delegate
                graphic_template = _substitute_wrapper_parameters(
                    delegate_spec.get("graphic_template"),
                    delegate_call["args"],
                )
            graphic_parameter = (
                re.search(r"#(?P<index>\d+)", graphic_template)
                if graphic_template else None
            )
            fixed_label_match = re.search(
                r"\\label\s*\{\s*(?P<label>[^#{}][^{}]*)\}", body
            )
            caption_index = (
                int(caption_match.group("index")) - 1 if caption_match else None
            )
            graphic_index = (
                int(graphic_parameter.group("index")) - 1
                if graphic_parameter else None
            )
            if caption_index is None and count >= 2:
                caption_index = count - 2
            label_index = int(label_match.group("index")) - 1 if label_match else None
            if label_index is None and count:
                label_index = count - 1
            if caption_index is not None and not 0 <= caption_index < count:
                continue
            if graphic_index is not None and not 0 <= graphic_index < count:
                continue
            if label_index is not None and not 0 <= label_index < count:
                continue
            specs[name] = {
                "total_count": count,
                "optional_default": optional_default,
                "graphic_index": graphic_index,
                "fixed_graphic": (
                    graphic_template if graphic_template and "#" not in graphic_template else None
                ),
                "graphic_template": graphic_template,
                "caption_index": caption_index,
                "fixed_caption": (
                    fixed_caption_match.group("caption").strip()
                    if fixed_caption_match else None
                ),
                "label_index": label_index,
                "fixed_label": (
                    fixed_label_match.group("label").strip()
                    if fixed_label_match else None
                ),
            }
            changed = True
    return specs


def _substitute_wrapper_parameters(template: str | None, arguments: list[str]) -> str | None:
    """Resolve ``#N`` placeholders for one small, fixed-arity wrapper call."""
    if template is None:
        return None
    unresolved = False

    def replace(match: re.Match) -> str:
        nonlocal unresolved
        index = int(match.group(1)) - 1
        if not 0 <= index < len(arguments):
            unresolved = True
            return match.group(0)
        return arguments[index]

    resolved = re.sub(r"#(\d+)", replace, template)
    return None if unresolved else resolved


def _figure_wrapper_calls(text: str, name: str, spec: dict) -> list[dict]:
    """Parse calls to one Figure wrapper, including one defaulted first arg."""
    calls: list[dict] = []
    pattern = re.compile(rf"\\(?P<name>{re.escape(name)})(?![A-Za-z@])", re.IGNORECASE)
    total_count = int(spec["total_count"])
    optional_default = spec["optional_default"]
    required_count = total_count - (optional_default is not None)
    for match in pattern.finditer(text):
        cursor = match.end()
        arguments: list[str] = []
        if optional_default is not None:
            optional, optional_end = _read_bracketed_argument(text, cursor)
            arguments.append(optional_default if optional is None else optional)
            if optional is not None:
                cursor = optional_end
        valid = True
        for _ in range(required_count):
            argument, end = _read_braced_argument(text, cursor)
            if argument is None:
                valid = False
                break
            arguments.append(argument)
            cursor = end
        if valid:
            calls.append({
                "name": match.group("name"),
                "args": arguments,
                "start": match.start(),
                "end": cursor,
            })
    return calls


def _large_figure_spans(
    text: str,
    wrapper_specs: dict[str, dict] | None = None,
) -> list[dict]:
    """Locate numbered top-level Figures; subpanels never count separately."""
    spans: list[dict] = []
    environment_spans: list[tuple[int, int]] = []
    for match in LARGE_FIGURE_ENV_RE.finditer(text):
        body = match.group("body")
        # A wrapper definition contains a template Figure with #2/#3.  The
        # definition is not a manuscript Figure; its calls are counted below.
        if re.search(r"#\d", body):
            continue
        labels = [
            label.strip()
            for label in LABEL_RE.findall(body)
            if label.strip() and "#" not in label
        ]
        captions = _caption_texts(body)
        if not captions:
            continue
        caption = captions[-1].strip() if captions else None
        label = labels[-1] if labels else f"figure@{match.start()}"
        spans.append({
            "kind": match.group("env"),
            "label": label,
            "bound_label": labels[-1] if labels else None,
            "caption": caption,
            "start": match.start(),
            "end": match.end(),
        })
        environment_spans.append((match.start(), match.end()))

    specs = _figure_wrapper_specs(text) if wrapper_specs is None else wrapper_specs
    for name, spec in specs.items():
        for call in _figure_wrapper_calls(text, name, spec):
            if any("#" in argument for argument in call["args"]):
                continue
            if any(start <= call["start"] < end for start, end in environment_spans):
                continue
            label_index = spec["label_index"]
            fixed_label = spec["fixed_label"]
            caption_index = spec["caption_index"]
            fixed_caption = spec["fixed_caption"]
            graphic_index = spec["graphic_index"]
            fixed_graphic = spec["fixed_graphic"]
            graphic_template = spec["graphic_template"]
            if graphic_template and "#" in graphic_template:
                graphic = _substitute_wrapper_parameters(graphic_template, call["args"])
            elif graphic_index is None:
                graphic = fixed_graphic
            else:
                graphic = call["args"][graphic_index].strip() or None
            if caption_index is None:
                caption = fixed_caption
            else:
                caption = call["args"][caption_index].strip() or None
            if label_index is None:
                label = fixed_label or f"{call['name']}@{call['start']}"
                bound_label = fixed_label
                if fixed_label:
                    label = f"{fixed_label}@{call['start']}"
            else:
                bound_label = call["args"][label_index].strip() or None
                label = bound_label or f"{call['name']}@{call['start']}"
            spans.append({
                "kind": call["name"],
                "label": label,
                "bound_label": bound_label,
                "caption": caption,
                "graphic": graphic,
                "start": call["start"],
                "end": call["end"],
            })
    return sorted(spans, key=lambda item: (item["start"], item["end"]))


def _figure_graphic_paths(text: str) -> list[str]:
    """Return executable direct and wrapper-bound graphic paths in source order."""
    active = _active_tex_source(text)
    body = _document_body_from_active_source(active)
    entries = [
        (match.start(), match.group(1).strip())
        for match in GRAPHICS_RE.finditer(body)
        if "#" not in match.group(1)
    ]
    for figure in _large_figure_spans(body, _figure_wrapper_specs(active)):
        graphic = figure.get("graphic")
        if graphic and figure["kind"].lower() not in {"figure", "figure*"}:
            entries.append((figure["start"], graphic))
    return [path for _, path in sorted(entries, key=lambda item: item[0])]


def _strip_invisible_bridge_content(text: str) -> str:
    """Remove common TeX constructs that create no normal-flow visible prose."""
    cleaned = _strip_balanced_command_groups(
        text,
        (
            "phantom", "hphantom", "vphantom", "rlap", "llap", "clap",
            "footnote", "footnotetext", "marginpar", "todo", "sidenote",
        ),
    )

    textcolor = re.compile(
        r"\\textcolor(?:\s*\[[^]]*\])?\s*"
        r"\{\s*(?:white|255\s*,\s*255\s*,\s*255)\s*\}",
        re.IGNORECASE,
    )
    while True:
        match = textcolor.search(cleaned)
        if match is None:
            break
        _, end = _read_braced_argument(cleaned, match.end())
        if end == match.end():
            break
        cleaned = cleaned[:match.start()] + cleaned[end:]

    # Stateful white text and zero-size fonts are hard to render statically.
    # Within a bridge gap, discard their span until an explicit reset; if no
    # reset is present, discard the remainder rather than credit invisible prose.
    cleaned = re.sub(
        r"\\color(?:\s*\[[^]]*\])?\s*"
        r"\{\s*(?:white|255\s*,\s*255\s*,\s*255)\s*\}.*?"
        r"(?=\\color(?:\s*\[[^]]*\])?\s*"
        r"\{\s*(?:black|auto|0\s*,\s*0\s*,\s*0)\s*\}|$)",
        " ",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    zero_scale = re.compile(
        r"\\scalebox\s*\{\s*0(?:\.0+)?\s*\}", re.IGNORECASE
    )
    while True:
        match = zero_scale.search(cleaned)
        if match is None:
            break
        _, end = _read_braced_argument(cleaned, match.end())
        if end == match.end():
            break
        cleaned = cleaned[:match.start()] + cleaned[end:]

    zero_resize = re.compile(
        r"\\resizebox\s*\{\s*0(?:\.0+)?\s*(?:pt|em|ex|mm|cm|in|bp)?\s*\}",
        re.IGNORECASE,
    )
    while True:
        match = zero_resize.search(cleaned)
        if match is None:
            break
        _, second_end = _read_braced_argument(cleaned, match.end())
        if second_end == match.end():
            break
        _, content_end = _read_braced_argument(cleaned, second_end)
        if content_end == second_end:
            break
        cleaned = cleaned[:match.start()] + cleaned[content_end:]
    cleaned = re.sub(
        r"\\fontsize\s*\{\s*0(?:\.0+)?\s*pt\s*\}\s*"
        r"\{\s*0(?:\.0+)?\s*pt\s*\}\s*\\selectfont.*?"
        r"(?=\\(?:normalsize|small|footnotesize|large|Large|LARGE)\b|$)",
        " ",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    white_group = re.compile(
        r"\{\s*\\color\s*\{\s*white\s*\}", re.IGNORECASE
    )
    while True:
        match = white_group.search(cleaned)
        if match is None:
            break
        _, end = _read_braced_argument(cleaned, match.start())
        if end == match.start():
            break
        cleaned = cleaned[:match.start()] + cleaned[end:]

    zero_width_box = re.compile(
        r"\\makebox\s*\[\s*0(?:\.0+)?(?:pt|em|ex|mm|cm|in|bp)?\s*\]"
        r"(?:\s*\[[^]]*\])?",
        re.IGNORECASE,
    )
    while True:
        match = zero_width_box.search(cleaned)
        if match is None:
            break
        _, end = _read_braced_argument(cleaned, match.end())
        if end == match.end():
            break
        cleaned = cleaned[:match.start()] + cleaned[end:]
    return cleaned


def _plain_bridge_paragraphs(text: str) -> list[str]:
    """Extract visible prose paragraphs between two top-level Figures."""
    cleaned = _strip_invisible_bridge_content(text)
    cleaned = re.sub(
        r"\\begin\s*\{(?:equation\*?|align\*?|alignat\*?|flalign\*?|"
        r"gather\*?|multline\*?|displaymath|eqnarray\*?|table\*?|longtable|"
        r"algorithm|algorithmic|lstlisting|Python|Matlab)\}.*?"
        r"\\end\s*\{(?:equation\*?|align\*?|alignat\*?|flalign\*?|"
        r"gather\*?|multline\*?|displaymath|eqnarray\*?|table\*?|longtable|"
        r"algorithm|algorithmic|lstlisting|Python|Matlab)\}",
        "\n\n",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(
        r"\\(?:part|chapter|section|subsection|subsubsection|paragraph|subparagraph)"
        r"\*?(?:\[[^]]*\])?\s*\{[^{}]*\}",
        "\n\n",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\\\[.*?\\\]|(?<!\\)\$\$.*?(?<!\\)\$\$", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"(?<!\\)\$(?:\\.|[^$])*?(?<!\\)\$", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(
        r"\\(?:ref|eqref|autoref|pageref|cite\w*)\s*\{[^{}]*\}",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\\label\s*\{[^{}]*\}", " ", cleaned, flags=re.IGNORECASE)
    chunks = re.split(r"\n\s*\n+", cleaned)
    paragraphs: list[str] = []
    for chunk in chunks:
        plain = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^]]*\])?", " ", chunk)
        plain = re.sub(r"[{}$~^_\\]", " ", plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        visible_count = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", plain))
        if visible_count >= 20:
            paragraphs.append(plain)
    return paragraphs


def analyze_large_figure_bridges(text: str) -> dict:
    """Ensure top-level Figures are separated by a substantive prose bridge."""
    active_source = _active_tex_source(text)
    body = _document_body_from_active_source(active_source)
    unresolved = "UNRESOLVED_TEX_CONDITIONAL" in active_source
    figures = _large_figure_spans(body, _figure_wrapper_specs(active_source))
    bridges: list[dict] = []
    for index, (previous, following) in enumerate(zip(figures, figures[1:]), start=1):
        paragraphs = _plain_bridge_paragraphs(body[previous["end"]:following["start"]])
        prose = " ".join(paragraphs)
        visible_count = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", prose))
        specific = FIGURE_BRIDGE_GENERIC_RE.sub("", prose)
        specific_count = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", specific))
        explains_previous = bool(FIGURE_BRIDGE_INTERPRET_RE.search(prose))
        motivates_next = bool(FIGURE_BRIDGE_NEXT_RE.search(prose))
        has_concrete_anchor = bool(FIGURE_BRIDGE_CONCRETE_RE.search(prose))
        ok = (
            bool(paragraphs)
            and visible_count >= 32
            and specific_count >= 10
            and explains_previous
            and motivates_next
            and has_concrete_anchor
        )
        bridges.append({
            "pair_index": index,
            "previous": previous["label"],
            "following": following["label"],
            "ok": ok,
            "substantive_paragraph_count": len(paragraphs),
            "visible_char_count": visible_count,
            "specific_char_count": specific_count,
            "explains_previous": explains_previous,
            "motivates_next": motivates_next,
            "has_concrete_anchor": has_concrete_anchor,
            "preview": prose[:180],
        })
    return {
        "ok": not unresolved and all(item["ok"] for item in bridges),
        "applicable": len(figures) >= 2,
        "source_resolved": not unresolved,
        "figure_count": len(figures),
        "figures": [
            {"kind": item["kind"], "label": item["label"]}
            for item in figures
        ],
        "bridges": bridges,
    }


def _table_column_specs(block: str) -> list[str]:
    """Extract column specifications from tabular-like environments."""
    specs: list[str] = []
    begin_re = re.compile(
        r"\\begin\s*\{(?P<env>tabularx|tabular\*?|longtable)\}",
        re.IGNORECASE,
    )
    for match in begin_re.finditer(block):
        cursor = match.end()
        while cursor < len(block) and block[cursor].isspace():
            cursor += 1
        if cursor < len(block) and block[cursor] == "[":
            closing = block.find("]", cursor + 1)
            if closing < 0:
                continue
            cursor = closing + 1
        env = match.group("env").lower()
        first, cursor = _read_braced_argument(block, cursor)
        if first is None:
            continue
        if env in {"tabularx", "tabular*"}:
            while cursor < len(block) and block[cursor].isspace():
                cursor += 1
            if cursor < len(block) and block[cursor] == "[":
                closing = block.find("]", cursor + 1)
                if closing < 0:
                    continue
                cursor = closing + 1
            second, _ = _read_braced_argument(block, cursor)
            if second is not None:
                specs.append(second)
        else:
            specs.append(first)
    return specs


def _symbol_table_rows(data: str) -> list[tuple[str, list[str]]]:
    """Return ordinary table rows and their cells, excluding rule/helper rows."""
    rows = []
    for row in re.split(r"\\\\(?:\s*\[[^]]*\])?", data):
        if "&" not in row or SYMBOL_PLACEHOLDER_RE.search(row):
            continue
        if re.search(r"\\(?:multicolumn|addlinespace|cmidrule|specialrule)\b", row):
            continue
        rows.append((row, re.split(r"(?<!\\)&", row)))
    return rows


def _symbol_data_rows(data: str, expected_columns: int) -> tuple[list[str], list[str]]:
    """Return complete rows and rows missing any declared field."""
    rows = []
    incomplete_rows = []
    for row, cells in _symbol_table_rows(data):
        meaningful = [_symbol_cell_has_visible_content(cell) for cell in cells]
        if len(cells) == expected_columns and all(meaningful):
            rows.append(row)
        else:
            incomplete_rows.append(row)
    return rows, incomplete_rows


def _strip_balanced_command_groups(text: str, names: tuple[str, ...]) -> str:
    command = re.compile(
        r"\\(?:" + "|".join(re.escape(name) for name in names) + r")\s*\{",
        re.IGNORECASE,
    )
    while True:
        match = command.search(text)
        if match is None:
            return text
        depth = 1
        cursor = match.end()
        while cursor < len(text) and depth:
            if text[cursor] == "{" and (cursor == 0 or text[cursor - 1] != "\\"):
                depth += 1
            elif text[cursor] == "}" and (cursor == 0 or text[cursor - 1] != "\\"):
                depth -= 1
            cursor += 1
        if depth:
            return text
        text = text[:match.start()] + text[cursor:]


def _symbol_cell_has_visible_content(cell: str) -> bool:
    plain = cell
    previous = None
    while previous != plain:
        previous = plain
        plain = _strip_balanced_command_groups(
            plain, ("phantom", "hphantom", "vphantom")
        )
        plain = re.sub(
            r"\\(?:text|mbox|makebox|textrm|textsf|texttt|mathrm|mathbf|mathit)"
            r"\s*\{\s*\}",
            "",
            plain,
            flags=re.IGNORECASE,
        )
        plain = re.sub(
            r"\\(?:smash|rlap|llap|clap|hbox|mbox|makebox)"
            r"(?:\s*\[[^]]*\])?\s*\{\s*\}",
            "",
            plain,
            flags=re.IGNORECASE,
        )
        plain = re.sub(
            r"\\(?:hspace|vspace)\*?\s*\{[^{}]*\}",
            "",
            plain,
            flags=re.IGNORECASE,
        )
        plain = re.sub(
            r"\\kern\s*[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
            r"(?:pt|em|ex|mu|mm|cm|in|pc|bp|dd|cc|sp)\b",
            "",
            plain,
            flags=re.IGNORECASE,
        )
        plain = re.sub(
            r"\\rule(?:\s*\[[^]]*\])?\s*"
            r"(?:\{\s*0(?:\.0+)?(?:pt|em|ex|mu|mm|cm|in|pc|bp|dd|cc|sp)?\s*\}\s*\{[^{}]*\}"
            r"|\{[^{}]*\}\s*\{\s*0(?:\.0+)?(?:pt|em|ex|mu|mm|cm|in|pc|bp|dd|cc|sp)?\s*\})",
            "",
            plain,
            flags=re.IGNORECASE,
        )
    plain = re.sub(r"\\(?:toprule|midrule|bottomrule|end\w+)\b", "", plain)
    plain = re.sub(
        r"\\(?:quad|qquad|enspace|thinspace|medspace|thickspace|"
        r"negthinspace|negmedspace|negthickspace|strut|null|hfill|vfill|relax)\b|\\[,;!:]",
        "",
        plain,
        flags=re.IGNORECASE,
    )
    plain = re.sub(r"[\s${}~]+", "", plain)
    return bool(plain)


def _active_font_size_command(text: str) -> str | None:
    """Track TeX font-size state across brace and environment groups."""
    token_re = re.compile(
        r"\\begin\s*\{(?P<begin>[^{}]+)\}|"
        r"\\end\s*\{(?P<end>[^{}]+)\}|"
        r"\\(?P<size>tiny|scriptsize|footnotesize|small|normalsize)\b|"
        r"(?P<open>(?<!\\)\{)|(?P<close>(?<!\\)\})",
        re.IGNORECASE,
    )
    active = None
    stack: list[str | None] = []
    for token in token_re.finditer(text):
        if token.group("begin") or token.group("open"):
            stack.append(active)
        elif token.group("end") or token.group("close"):
            if stack:
                active = stack.pop()
        elif token.group("size"):
            name = token.group("size").lower()
            active = None if name == "normalsize" else name
    return active


def analyze_symbol_glossary(text: str) -> dict:
    """Audit the user-required main-symbol three-line table.

    ``text`` should normally be the fully expanded paper source.  Comments are
    removed again here so a commented-out heading, rule or row cannot satisfy
    the contract.  The returned component fields are intentionally reusable by
    :mod:`paper_checklist` as well as the release source audit.
    """
    cleaned = remove_inactive_regions(remove_comments(text))
    document_begin = re.search(r"\\begin\s*\{document\}", cleaned, re.IGNORECASE)
    if document_begin:
        document_end = re.search(
            r"\\end\s*\{document\}", cleaned[document_begin.end():], re.IGNORECASE
        )
        if document_end:
            cleaned = cleaned[
                document_begin.end():document_begin.end() + document_end.start()
            ]
    headings = list(STRUCTURAL_HEADING_RE.finditer(cleaned))
    rank = {"section": 1, "subsection": 2, "subsubsection": 3}

    symbol_headings = [
        heading for heading in headings
        if _is_symbol_glossary_title(heading.group("title"))
    ]
    symbol_heading = symbol_headings[0] if symbol_headings else None
    question_heading = next(
        (heading for heading in headings
         if NUMBERED_QUESTION_TITLE_RE.search(heading.group("title"))),
        None,
    )

    result = {
        "ok": False,
        "structure_ok": False,
        "metadata_ok": False,
        "heading_found": symbol_heading is not None,
        "symbol_heading_count": len(symbol_headings),
        "heading_title": symbol_heading.group("title").strip() if symbol_heading else None,
        "heading_level": symbol_heading.group("kind").lower() if symbol_heading else None,
        "first_numbered_question": (
            question_heading.group("title").strip() if question_heading else None
        ),
        "before_first_numbered_question": False,
        "before_first_display_math": False,
        "after_existing_preliminary_sections": False,
        "preliminary_headings": [],
        "tables_in_symbol_section": 0,
        "single_table_in_symbol_section": False,
        "target_table_found": False,
        "target_environment": None,
        "inner_tabular_count": 0,
        "bound_data_environment": None,
        "caption": None,
        "caption_contains_symbol": False,
        "labels": [],
        "unique_label": False,
        "reference_before_table": False,
        "rules": {"toprule": False, "midrule": False, "bottomrule": False},
        "rules_in_order": False,
        "header_has_symbol": False,
        "header_has_meaning": False,
        "header_cells_complete": False,
        "header_semantics_separate": False,
        "header_cells": [],
        "expected_column_count": 0,
        "data_row_count": 0,
        "incomplete_data_rows": [],
        "forbidden_grid_commands": [],
        "forbidden_scaling_or_tiny_commands": [],
        "column_specs": [],
        "column_format_has_vertical_rule": False,
        "placeholders": [],
        "structure_failures": [],
        "metadata_failures": [],
        "failures": [],
        "unresolved_conditionals": "UNRESOLVED_TEX_CONDITIONAL" in cleaned,
    }

    if result["unresolved_conditionals"]:
        result["structure_failures"].append(
            "论文源含无法静态判定或未配对的 TeX 条件分支，不能用其内容通过符号表审计"
        )

    if symbol_heading is None:
        result["structure_failures"].append("未找到明确的“主要符号/符号说明”标题")
        result["metadata_failures"].append("缺少主要符号表，无法核验题注、标签与正文引用")
        result["failures"] = result["structure_failures"] + result["metadata_failures"]
        return result
    if len(symbol_headings) != 1:
        result["structure_failures"].append("全文必须且只能有一个独立的主要符号说明标题")

    result["before_first_numbered_question"] = (
        question_heading is None or symbol_heading.start() < question_heading.start()
    )
    if not result["before_first_numbered_question"]:
        result["structure_failures"].append("主要符号说明必须位于第一道编号问题之前")
    relevant_preliminary = [
        heading for heading in headings
        if PRE_SYMBOL_TITLE_RE.fullmatch(re.sub(r"\s+", "", heading.group("title")))
        and (question_heading is None or heading.start() < question_heading.start())
    ]
    result["preliminary_headings"] = [
        heading.group("title").strip() for heading in relevant_preliminary
    ]
    result["after_existing_preliminary_sections"] = all(
        heading.start() < symbol_heading.start() for heading in relevant_preliminary
    )
    if not result["after_existing_preliminary_sections"]:
        result["structure_failures"].append(
            "若存在总体问题分析、数据审计或假设章节，主要符号说明必须位于这些章节之后"
        )

    symbol_rank = rank[symbol_heading.group("kind").lower()]
    section_end = len(cleaned)
    for heading in headings:
        if heading.start() <= symbol_heading.start():
            continue
        if rank[heading.group("kind").lower()] <= symbol_rank:
            section_end = heading.start()
            break
    section_body = cleaned[symbol_heading.end():section_end]
    tables = list(SYMBOL_TABLE_ENV_RE.finditer(section_body))
    result["tables_in_symbol_section"] = len(tables)
    result["single_table_in_symbol_section"] = len(tables) == 1
    if not tables:
        result["structure_failures"].append("符号说明段内未找到 table/table*/longtable")
        result["metadata_failures"].append("符号说明段内没有可核验题注与标签的表格")
        result["failures"] = result["structure_failures"] + result["metadata_failures"]
        return result

    def caption_text(table_match: re.Match) -> str | None:
        table_text = table_match.group(0)
        match = re.search(r"\\caption(?:\[[^]]*\])?", table_text, re.S)
        if not match:
            return None
        value, _ = _read_braced_argument(table_text, match.end())
        return re.sub(r"\s+", " ", value).strip() if value is not None else None

    target = next(
        (table for table in tables if "符号" in (caption_text(table) or "")),
        tables[0],
    )
    block = target.group(0)
    result["target_table_found"] = True
    result["target_environment"] = target.group("env")
    result["caption"] = caption_text(target)
    result["caption_contains_symbol"] = bool(result["caption"] and "符号" in result["caption"])

    if target.group("env").lower() == "longtable":
        data_block = block
        result["inner_tabular_count"] = 1
        result["bound_data_environment"] = "longtable"
    else:
        inner_tables = list(INNER_TABULAR_ENV_RE.finditer(block))
        result["inner_tabular_count"] = len(inner_tables)
        if len(inner_tables) == 1:
            data_block = inner_tables[0].group(0)
            result["bound_data_environment"] = inner_tables[0].group("env")
        else:
            data_block = ""

    labels = LABEL_RE.findall(block)
    result["labels"] = labels
    result["unique_label"] = (
        len(labels) == 1 and LABEL_RE.findall(cleaned).count(labels[0]) == 1
    )
    refs_before_table = REF_RE.findall(section_body[:target.start()])
    result["reference_before_table"] = bool(
        len(labels) == 1 and labels[0] in refs_before_table
    )

    rule_positions = {
        rule: [match.start() for match in re.finditer(rf"\\{rule}\b", data_block)]
        for rule in ("toprule", "midrule", "bottomrule")
    }
    positions = {
        "toprule": rule_positions["toprule"][0] if rule_positions["toprule"] else -1,
        "midrule": rule_positions["midrule"][0] if rule_positions["midrule"] else -1,
        "bottomrule": rule_positions["bottomrule"][-1] if rule_positions["bottomrule"] else -1,
    }
    result["rules"] = {rule: position >= 0 for rule, position in positions.items()}
    result["rule_counts"] = {
        rule: len(found) for rule, found in rule_positions.items()
    }
    result["rules_in_order"] = (
        positions["toprule"] >= 0
        and positions["toprule"] < positions["midrule"] < positions["bottomrule"]
    )

    if result["rules_in_order"]:
        header = data_block[positions["toprule"] + len(r"\toprule"):positions["midrule"]]
        header_rows = _symbol_table_rows(header)
        if header_rows:
            header_cells = header_rows[0][1]
            visible_cells = [
                _symbol_cell_has_visible_content(cell) for cell in header_cells
            ]
            symbol_columns = [
                index for index, cell in enumerate(header_cells)
                if visible_cells[index] and "符号" in cell
            ]
            meaning_columns = [
                index for index, cell in enumerate(header_cells)
                if visible_cells[index] and re.search(r"含义|定义|说明", cell)
            ]
            result["header_cells"] = header_cells
            result["header_cells_complete"] = all(visible_cells)
            result["header_has_symbol"] = bool(symbol_columns)
            result["header_has_meaning"] = bool(meaning_columns)
            result["header_semantics_separate"] = any(
                symbol_index != meaning_index
                for symbol_index in symbol_columns
                for meaning_index in meaning_columns
            )
            result["expected_column_count"] = len(header_cells)
        longtable_markers = list(re.finditer(
            r"\\end(?:firsthead|head|foot|lastfoot)\b", data_block, re.IGNORECASE
        ))
        data_start = (
            longtable_markers[-1].end()
            if result["bound_data_environment"] == "longtable" and longtable_markers
            else positions["midrule"] + len(r"\midrule")
        )
        data_end = (
            data_block.lower().rfind(r"\end{longtable}")
            if result["bound_data_environment"] == "longtable" and longtable_markers
            else positions["bottomrule"]
        )
        data = data_block[data_start:data_end]
        result["data_has_rule_commands"] = bool(re.search(
            r"\\(?:toprule|midrule|bottomrule|cmidrule|specialrule|hline|cline|hhline)\b",
            data,
            re.IGNORECASE,
        ))
        data_rows, incomplete_rows = _symbol_data_rows(
            data, result["expected_column_count"]
        )
        result["data_row_count"] = len(data_rows)
        result["incomplete_data_rows"] = incomplete_rows

    result["forbidden_grid_commands"] = sorted(set(re.findall(
        r"\\(?:hline|cline|vline|vrule)\b", data_block, re.IGNORECASE
    )))
    result["extra_visible_rule_commands"] = sorted(set(re.findall(
        r"\\(?:cmidrule|specialrule|hhline)\b", data_block, re.IGNORECASE
    )))
    block_start = symbol_heading.end() + target.start()
    block_end = symbol_heading.end() + target.end()
    first_display_math = DISPLAY_MATH_RE.search(cleaned)
    result["before_first_display_math"] = (
        first_display_math is None or block_end < first_display_math.start()
    )
    if not result["before_first_display_math"]:
        result["structure_failures"].append("主符号表必须位于全文首个展示型模型公式之前")
    data_offset = block.find(data_block) if data_block else 0
    active_size = _active_font_size_command(cleaned[:block_start + data_offset])
    scaling_commands = re.findall(r"\\(?:resizebox|scalebox)\b", block, re.IGNORECASE)
    data_size_commands = re.findall(
        r"\\(?:tiny|scriptsize|footnotesize|small)\b", data_block, re.IGNORECASE
    )
    result["forbidden_scaling_or_tiny_commands"] = sorted(set(
        scaling_commands + data_size_commands + ([f"\\{active_size}"] if active_size else [])
    ))
    result["column_specs"] = _table_column_specs(data_block)
    result["column_format_has_vertical_rule"] = any(
        "|" in spec for spec in result["column_specs"]
    )
    result["placeholders"] = sorted(set(
        match.group(0) for match in SYMBOL_PLACEHOLDER_RE.finditer(section_body)
    ))

    structure_requirements = [
        (result["target_table_found"], "符号说明段内缺少目标表格"),
        (result["single_table_in_symbol_section"], "符号说明段必须且只能包含一张主符号表"),
        (
            result["inner_tabular_count"] == 1,
            "目标 table 内必须且只能包含一个实际 tabular/tabularx；longtable 自身作为唯一数据表",
        ),
        (result["rules_in_order"], "目标数据表必须在同一 tabular/longtable 内依次使用 top/mid/bottomrule"),
        (
            result["bound_data_environment"] == "longtable"
            or all(result.get("rule_counts", {}).get(rule) == 1 for rule in ("toprule", "midrule", "bottomrule")),
            "普通符号表必须且只能各使用一次 top/mid/bottomrule",
        ),
        (
            not result.get("data_has_rule_commands", False),
            "符号表真实数据区不得夹入额外横线命令",
        ),
        (result["header_has_symbol"], "符号表表头缺少“符号”列"),
        (result["header_has_meaning"], "符号表表头缺少“含义/定义/说明”列"),
        (result["header_cells_complete"], "符号表每个已声明表头单元格都必须有可见内容"),
        (
            result["header_semantics_separate"],
            "“符号”与“含义/定义/说明”必须位于两个不同表头单元格",
        ),
        (result["expected_column_count"] >= 2, "符号表表头必须声明至少两列"),
        (result["data_row_count"] >= 1, "符号表至少需要一条真实数据行"),
        (
            not result["incomplete_data_rows"],
            "符号表数据行必须与表头列数一致，且每个已声明字段均不得留空",
        ),
        (not result["forbidden_grid_commands"], "符号表不得使用 hline/cline/vline 网格线"),
        (
            not result["extra_visible_rule_commands"],
            "符号表除 top/mid/bottomrule 外不得使用 cmidrule/specialrule/hhline 额外横线",
        ),
        (
            not result["forbidden_scaling_or_tiny_commands"],
            "符号表不得使用 resizebox/scalebox 或 small/footnotesize/scriptsize/tiny 缩放挤压",
        ),
        (len(result["column_specs"]) == 1, "目标数据表必须具有唯一且可解析的列格式"),
        (not result["column_format_has_vertical_rule"], "符号表列格式不得包含竖线"),
        (not result["placeholders"], "符号说明段仍含占位文本"),
    ]
    result["structure_failures"].extend(
        message for ok, message in structure_requirements if not ok
    )

    metadata_requirements = [
        (result["caption_contains_symbol"], "符号表题注缺失或题注未明确包含“符号”"),
        (result["unique_label"], "符号表必须且只能有一个全局唯一 label"),
        (result["reference_before_table"], "符号表前正文必须用 ref 引用该表 label"),
    ]
    result["metadata_failures"].extend(
        message for ok, message in metadata_requirements if not ok
    )
    result["structure_ok"] = not result["structure_failures"]
    result["metadata_ok"] = not result["metadata_failures"]
    result["ok"] = result["structure_ok"] and result["metadata_ok"]
    result["failures"] = result["structure_failures"] + result["metadata_failures"]
    return result


def _chinese_question_number(token: str) -> int | None:
    """Convert the small Chinese numerals used in problem headings to an integer."""
    token = token.strip()
    if token.isdigit():
        value = int(token)
        return value if value > 0 else None
    digits = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    units = {"十": 10, "百": 100}
    total = 0
    current = 0
    for char in token:
        if char in digits:
            current = digits[char]
        elif char in units:
            total += (current or 1) * units[char]
            current = 0
        else:
            return None
    value = total + current
    return value if value > 0 else None


def question_number(title: str) -> int | None:
    """Return the canonical positive integer for a numbered-question title."""
    match = QUESTION_NUMBER_RE.match(title)
    if not match:
        return None
    token = next((value for value in match.groupdict().values() if value), "")
    return _chinese_question_number(token)


def _question_alias_key(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    return re.sub(r"[\s:：、，,。．.；;_-]+", "", text)


def manifest_question_expectations(manifest: dict) -> dict:
    """Resolve numbered questions and their aliases from problem chapter records."""
    expected: list[dict] = []
    errors: list[str] = []
    number_owner: dict[int, str] = {}
    alias_to_number: dict[str, int] = {}
    for chapter in manifest.get("chapters", []):
        if str(chapter.get("role", "")).strip().lower() != "problem":
            continue
        title = str(chapter.get("title", "")).strip()
        raw_aliases = chapter.get("aliases", [])
        aliases = [str(item).strip() for item in raw_aliases] if isinstance(raw_aliases, list) else []
        labels = [item for item in [title, *aliases] if item]
        numbers = {value for value in (question_number(item) for item in labels) if value is not None}
        chapter_id = str(chapter.get("chapter_id", title or "<unnamed>"))
        if len(numbers) > 1:
            errors.append(
                f"问题章节 {chapter_id} 的 title/aliases 指向多个编号: {sorted(numbers)}"
            )
            continue
        if not numbers:
            # A role=problem chapter such as “问题重述” is not necessarily one
            # of the numbered contest questions and must not be coerced into Q1.
            continue
        number = next(iter(numbers))
        previous = number_owner.get(number)
        if previous is not None:
            errors.append(f"编号问题 {number} 被多个章节重复登记: {previous}, {chapter_id}")
            continue
        number_owner[number] = chapter_id
        expected.append({
            "number": number,
            "chapter_id": chapter_id,
            "title": title,
            "aliases": aliases,
        })
        for label in labels:
            key = _question_alias_key(label)
            owner = alias_to_number.get(key)
            if owner is not None and owner != number:
                errors.append(f"问题标题别名 {label!r} 同时指向编号 {owner} 与 {number}")
            else:
                alias_to_number[key] = number
    return {
        "expected": expected,
        "expected_numbers": [item["number"] for item in expected],
        "alias_to_number": alias_to_number,
        "errors": errors,
    }


def _question_opener_policy(manifest: dict, has_expected: bool) -> dict:
    """Validate the optional explicit waiver for papers without numbered questions."""
    raw = manifest.get("question_openers")
    if raw is None:
        return {"declared": False, "required": has_expected, "reason": "", "errors": []}
    if (
        not isinstance(raw, dict)
        or bool(set(raw) - {"required", "reason"})
        or type(raw.get("required")) is not bool
        or ("reason" in raw and not isinstance(raw["reason"], str))
    ):
        return {
            "declared": True,
            "required": None,
            "reason": "",
            "errors": ["question_openers 必须是仅含布尔 required 与可选字符串 reason 的对象"],
        }
    required = raw["required"]
    reason = str(raw.get("reason", "")).strip()
    errors: list[str] = []
    if not required and len(reason) < 8:
        errors.append("question_openers.required=false 时必须给出至少 8 字的不适用理由")
    if not required and has_expected:
        errors.append("manifest 已登记编号问题，不得将逐问导读声明为不适用")
    if required and not has_expected:
        errors.append("question_openers.required=true 时必须在 problem 章节 title/aliases 登记编号")
    return {
        "declared": True,
        "required": required,
        "reason": reason,
        "errors": errors,
    }


def question_opener_manifest_contract(manifest: dict) -> dict:
    """Return the shared manifest-only contract used by builders and source audit."""
    registration = manifest_question_expectations(manifest)
    policy = _question_opener_policy(manifest, bool(registration["expected_numbers"]))
    errors = [*registration["errors"], *policy["errors"]]
    return {
        "ok": not errors,
        "expected_questions": registration["expected"],
        "expected_numbers": registration["expected_numbers"],
        "alias_to_number": registration["alias_to_number"],
        "policy": policy,
        "registration_errors": registration["errors"],
        "errors": errors,
    }


def audit_question_openers(
    text: str,
    alias_to_number: dict[str, int] | None = None,
) -> list[dict]:
    """Check that numbered or manifest-aliased problem sections open with guidance."""
    cleaned = remove_comments(text)
    appendix_pos = cleaned.find(r"\appendix")
    if appendix_pos >= 0:
        cleaned = cleaned[:appendix_pos]
    section_starts = [match.start() for match in ANY_SECTION_RE.finditer(cleaned)]
    findings: list[dict] = []
    aliases = alias_to_number or {}
    section_matches = [
        match
        for match in STRUCTURAL_HEADING_RE.finditer(cleaned)
        if match.group("kind").lower() == "section"
    ]
    for match in section_matches:
        title = re.sub(r"\s+", " ", match.group("title")).strip()
        number = question_number(title)
        if number is None:
            number = aliases.get(_question_alias_key(title))
        if number is None:
            continue
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
            "title": title,
            "question_number": number,
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


def audit_manifest_question_openers(manifest: dict, text: str) -> dict:
    """Require one valid opener for every numbered question registered in the manifest."""
    contract = question_opener_manifest_contract(manifest)
    expected_numbers = contract["expected_numbers"]
    policy = contract["policy"]
    findings = audit_question_openers(text, contract["alias_to_number"])
    actual_numbers = [item["question_number"] for item in findings]
    counts = {number: actual_numbers.count(number) for number in set(actual_numbers)}
    duplicate_numbers = sorted(number for number, count in counts.items() if count > 1)
    missing_numbers = [number for number in expected_numbers if number not in counts]
    unexpected_numbers = sorted(set(actual_numbers) - set(expected_numbers))
    invalid_numbers = sorted({
        item["question_number"]
        for item in findings
        if item["question_number"] in expected_numbers and not item["ok"]
    })
    errors = contract["errors"]
    ok = (
        not errors
        and not missing_numbers
        and not unexpected_numbers
        and not duplicate_numbers
        and not invalid_numbers
    )
    return {
        "ok": ok,
        "applicable": bool(expected_numbers),
        "policy": policy,
        "expected_questions": contract["expected_questions"],
        "expected_numbers": expected_numbers,
        "actual_numbers": actual_numbers,
        "missing_numbers": missing_numbers,
        "unexpected_numbers": unexpected_numbers,
        "duplicate_numbers": duplicate_numbers,
        "invalid_opener_numbers": invalid_numbers,
        "registration_errors": contract["registration_errors"],
        "errors": errors,
        "sections": findings,
    }


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


def audit(
    manifest_path: Path,
    main_path: Path,
    require_filled_cover: bool = False,
) -> dict:
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

    chapters = manifest.get("chapters", [])
    reference_chapters = [
        chapter for chapter in chapters
        if str(chapter.get("role", "")).strip() == "references"
    ]
    add(
        "manifest_has_exactly_one_references_chapter",
        len(reference_chapters) == 1,
        count=len(reference_chapters),
        chapter_ids=[chapter.get("chapter_id") for chapter in reference_chapters],
        message="manifest 必须且只能声明一个 references 章节。",
    )

    terminal_page_starts = []
    for chapter in chapters:
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
        len(reference_chapters) == 1
        and all(item["has_clearpage"] for item in terminal_page_starts),
        chapters=terminal_page_starts,
        message="参考文献与每个附录入口前必须用 \\clearpage 清空浮动体并另起一页。",
    )

    # Attachment 2 states that the page after the complete abstract begins
    # the body.  A generated table of contents between them is non-compliant.
    abstract_begin = clean_main.find(r"\begin{abstract}")
    abstract_end = clean_main.find(r"\end{abstract}")
    abstract_main = (
        clean_main[abstract_begin:abstract_end]
        if 0 <= abstract_begin < abstract_end else ""
    )
    abstract_fragment = ""
    abstract_fragment_errors: list[str] = []
    try:
        abstract_path = inside(root, expected[0])
    except (ValueError, OSError) as exc:
        abstract_fragment_errors.append(str(exc))
    else:
        if abstract_path.is_file():
            abstract_fragment, abstract_fragment_errors = expand_tex_in_order(
                abstract_path,
                project_root,
                base=root,
            )
        else:
            abstract_fragment_errors.append(f"abstract fragment does not exist: {abstract_path}")
    abstract_violations = abstract_layout_violations(abstract_main + "\n" + abstract_fragment)
    add(
        "abstract_uses_internal_one_page_layout",
        abstract_begin >= 0
        and abstract_end > abstract_begin
        and not abstract_fragment_errors
        and not abstract_violations,
        violations=abstract_violations,
        expansion_errors=abstract_fragment_errors,
        message=(
            "一页摘要必须靠精炼题目与内容实现；禁止在摘要中缩字号、改行距、缩放、"
            "负向挤压或手工分页。实际页数与题目行数以编译 PDF 的 audit_paper.py 为准。"
        ),
    )
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
    layout_overrides = page_layout_overrides(main_text)
    add(
        "main_does_not_override_official_geometry",
        not layout_overrides,
        overrides=layout_overrides,
        message="页边距由 gmcmthesis.cls 统一设为官方 Word 模板的 30/17.5/22.5/22.5 mm。",
    )
    cover_pos = clean_main.find(r"\makeidentitycover")
    title_pos = clean_main.find(r"\maketitle")
    cover_matches = {
        command: re.search(rf"\\{command}\s*\{{([^{{}}]*)\}}", clean_main, re.S)
        for command in COVER_FIELD_NAMES
    }
    cover_fields = {command: match is not None for command, match in cover_matches.items()}
    cover_fields_filled = {
        command: bool(
            match
            and _symbol_cell_has_visible_content(match.group(1))
            and not COVER_VALUE_PLACEHOLDER_RE.search(match.group(1))
        )
        for command, match in cover_matches.items()
    }
    add(
        "uses_required_identity_cover",
        cover_pos >= 0 and title_pos > cover_pos and all(cover_fields.values()),
        fields=cover_fields,
        message="2026 正式提交：先输出第 0 页封皮，再输出页码 1 的匿名摘要页。",
    )
    add(
        "identity_cover_fields_filled_for_submission",
        not require_filled_cover or all(cover_fields_filled.values()),
        required=require_filled_cover,
        fields=cover_fields_filled,
        message=(
            "正式提交审计要求学校、参赛队号和三名队员姓名均为非空、非占位值；"
            "脚手架源审计可保留空字段。"
        ),
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

    appendix_chapters = [
        chapter for chapter in manifest.get("chapters", [])
        if str(chapter.get("role", "")).strip() == "appendix"
    ]
    appendix_roots: list[Path] = []
    appendix_path_errors: list[str] = []
    for chapter in appendix_chapters:
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

    policy = manifest.get("appendix_pseudocode")
    policy_ok = (
        isinstance(policy, dict)
        and not set(policy) - {"required", "reason"}
        and type(policy.get("required")) is bool
        and ("reason" not in policy or isinstance(policy["reason"], str))
    )
    required_value = policy.get("required") if policy_ok else True
    reason = policy.get("reason", "").strip() if policy_ok else ""
    if policy_ok and required_value is False:
        policy_ok = (
            len(reason) >= 8
            and not MANIFEST_REASON_SENTINEL_RE.search(reason)
            and bool(re.search(
                r"纯解析|解析推导|理论推导|闭式|证明|不依赖|不涉及|无需|未使用|没有使用|"
                r"analytic|closed[- ]form|proof|without|does not",
                reason,
                re.IGNORECASE,
            ))
        )
    pseudocode_required = required_value if policy_ok else True
    add(
        "appendix_pseudocode_policy_valid",
        policy_ok,
        explicit="appendix_pseudocode" in manifest,
        required=pseudocode_required,
        reason=reason,
        errors=appendix_errors,
        message=(
            "manifest 必须显式裁决 appendix_pseudocode：计算型设 required=true；"
            "纯解析题可设 required=false，并给出至少 8 字且说明不依赖程序/数值计算的具体理由。"
        ),
    )
    appendix_declared = bool(appendix_chapters)
    add(
        "appendix_pseudocode_required_has_appendix",
        not pseudocode_required or appendix_declared,
        required=pseudocode_required,
        appendix_chapters=[chapter.get("chapter_id") for chapter in appendix_chapters],
        message="appendix_pseudocode.required=true 时必须在 manifest 中声明 appendix 章节。",
    )

    code_blocks = [match.group("body") for match in CODE_BLOCK_RE.finditer(appendix_text)]
    has_code_block = bool(code_blocks)
    appendix_context = "\n".join(
        [appendix_text, *(str(chapter.get("title", "")) for chapter in appendix_chapters)]
    )
    pseudocode_claimed = has_code_block or bool(re.search(
        r"伪代码|代码式|代码框架|pseudocode|code\s+framework",
        appendix_context,
        re.IGNORECASE,
    ))
    code_validation_required = pseudocode_required or pseudocode_claimed
    add(
        "appendix_has_code_style_pseudocode",
        not code_validation_required or (
            appendix_declared and not appendix_errors and has_code_block
        ),
        applicable=code_validation_required,
        required=pseudocode_required,
        claimed=pseudocode_claimed,
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
        not code_validation_required or (has_code_block and traceable),
        applicable=code_validation_required,
        required=pseudocode_required,
        claimed=pseudocode_claimed,
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
    symbol_glossary = analyze_symbol_glossary(expanded_paper)
    symbol_glossary_ok = not question_expansion_errors and symbol_glossary["ok"]
    add(
        "main_symbol_glossary_is_complete_three_line_table",
        symbol_glossary_ok,
        analysis=symbol_glossary,
        expansion_errors=question_expansion_errors,
        message=(
            "这是用户确认的内部成稿规则，并非官方附件明文要求：正文须在第一道编号问题前"
            "设置可引用的主要符号三线表；表内至少一条真实数据行，且不得使用网格线或占位符。"
        ),
    )
    question_openers = audit_manifest_question_openers(manifest, expanded_paper)
    add(
        "question_sections_open_with_recap_route_and_deliverable",
        not question_expansion_errors and question_openers["ok"],
        applicable=question_openers["applicable"],
        policy=question_openers["policy"],
        expected_questions=question_openers["expected_questions"],
        expected_numbers=question_openers["expected_numbers"],
        actual_numbers=question_openers["actual_numbers"],
        missing_numbers=question_openers["missing_numbers"],
        unexpected_numbers=question_openers["unexpected_numbers"],
        duplicate_numbers=question_openers["duplicate_numbers"],
        invalid_opener_numbers=question_openers["invalid_opener_numbers"],
        registration_errors=question_openers["registration_errors"],
        sections=question_openers["sections"],
        expansion_errors=question_expansion_errors,
        message=(
            "每个编号问题须在首个小标题、公式或图表前，用至少两句实质正文完成"
            "题意/承接回溯、方法路线和结果交付定位；预期问题由 manifest 中 role=problem "
            "章节的 title/aliases 决定，不得漏章、重号或以别名绕过。无编号问题可用 "
            "question_openers.required=false 和具体理由显式声明不适用。"
        ),
    )
    figure_bridges = analyze_large_figure_bridges(expanded_paper)
    add(
        "large_figures_have_narrative_bridges",
        not question_expansion_errors and figure_bridges["ok"],
        analysis=figure_bridges,
        expansion_errors=question_expansion_errors,
        message=(
            "这是用户确认的内部阅读节奏规则，并非官方明文要求：任意两张相邻顶层 Figure "
            "之间至少保留一段实质正文，完成上一图证据解释、承接理由和下一图目的；"
            "复杂关系建议用两段。标题、分页命令或‘下面给出下一图’不算过渡，子图面板不另计。"
        ),
    )

    missing_graphics: list[str] = []
    for raw in _figure_graphic_paths(expanded_paper):
        try:
            # The paper source may reference real result figures stored in
            # the sibling 求解/ tree.  Inputs remain confined to 论文/;
            # graphics are allowed anywhere inside the project root.
            path = (main_path.parent / decode_tex_path(raw)).resolve()
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
    parser.add_argument(
        "--require-filled-cover",
        action="store_true",
        help="按正式提交模式要求封皮五个身份字段均已填写；默认仅审脚手架结构。",
    )
    args = parser.parse_args()
    result = audit(
        args.manifest.resolve(),
        args.main.resolve(),
        require_filled_cover=args.require_filled_cover,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
