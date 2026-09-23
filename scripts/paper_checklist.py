#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_checklist.py — 优秀论文自检表机检脚本（Wave6-A）。

对 .tex（必做）/ .docx（尽力做）论文运行 138 条自检表中可确定性检查的条目，
输出 Markdown 报告，并在论文目录生成《论文自检表_已勾选.md》。

人工条目（字体、配色、叙事流畅度等）输出 ☐ 待人工；用 --mark ID=pass|na 记录裁决，
持久化到论文目录旁的 paper_checklist_decisions.json。--strict 模式下任何机检 fail/pending
或人工条目未裁决都会失败。

用法：
  python scripts/paper_checklist.py --tex path/to/main.tex --problems 3 --archetype optimization
  python scripts/paper_checklist.py --tex main.tex --mark Q08=pass --note "图均有正文引用"
  python scripts/paper_checklist.py --tex main.tex --strict
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from audit_tex import (
    _active_tex_source,
    _caption_texts,
    _document_body_from_active_source,
    _figure_wrapper_specs,
    _large_figure_spans,
    _read_braced_argument,
    analyze_symbol_glossary,
    expand_tex_in_order,
    find_project_root,
)
from progress import build_provenance

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKLIST_JSON = REPO_ROOT / "assets" / "checklists" / "paper_checklist.json"
DECISIONS_NAME = "paper_checklist_decisions.json"
REPORT_NAME = "论文自检表_已勾选.md"

ARCHETYPES = {
    "optimization", "evaluation", "prediction", "classification-cv",
    "mechanism", "signal", "spatial-graph", "simulation",
}

TEX_ONLY_PENDING = (
    "未提供可读 TeX 源稿，无法可靠判定；请运行 "
    "scripts/audit_docx.py --docx <论文.docx> --report <审计报告.json> "
    "完成 DOCX 专项审计"
)

# 章节关键词（按出现顺序切分；首个 \section 之前的内容归 "preamble"）
SECTION_KEYWORDS = [
    ("abstract", ["摘要", "abstract"]),
    ("intro", ["引言", "引言", "问题提出", "problem background"]),
    ("overall", ["总体分析", "问题分析", "总体设计"]),
    ("assumption", ["模型假设", "基本假设", "假设"]),
    ("symbol", ["符号说明", "符号表", "主要符号"]),
    ("analysis", ["具体分析"]),
    ("prep", ["模型准备", "数据预处理", "预处理"]),
    ("building", ["模型建立", "模型构建"]),
    ("solving", ["模型求解", "模型求解与"]),
    ("check", ["模型检验", "检验与分析", "灵敏度分析", "误差分析"]),
    ("eval", ["模型的评价", "模型评价", "优缺点", "模型的优缺点"]),
    ("improve", ["模型的改进", "改进"]),
    ("extend", ["模型的推广", "推广"]),
    ("ref", ["参考文献", "references", "bibliography"]),
    ("appendix", ["附录", "appendix"]),
]


@dataclass
class CheckResult:
    item_id: str
    status: str  # "pass" | "fail" | "pending" | "na" | "skip"
    evidence: str = ""
    detail: str = ""


@dataclass
class PaperContext:
    tex_path: Optional[Path]
    docx_path: Optional[Path]
    tex_text: str = ""
    tex_lines: list = field(default_factory=list)
    sections: dict = field(default_factory=dict)  # key -> (start_line, end_line, text)
    problems: Optional[int] = None
    archetype: Optional[str] = None
    decisions: dict = field(default_factory=dict)
    tex_expansion_errors: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# 解析
# --------------------------------------------------------------------------- #
def load_checklist() -> dict:
    return json.loads(CHECKLIST_JSON.read_text(encoding="utf-8"))


def split_sections(tex: str) -> tuple[dict, list]:
    """按 \\section{...} 切分章节。返回 {key: (start, end, text)} 与顺序列表。"""
    lines = tex.splitlines()
    # 找所有 \section{...} / \section*{...} 位置
    sec_re = re.compile(r"^\s*\\section\*?\s*\{([^}]*)\}")
    hits: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        m = sec_re.match(ln)
        if m:
            hits.append((i, m.group(1).strip()))
    sections: dict[tuple[int, int, str]] = {}
    order = []
    for idx, (start, title) in enumerate(hits):
        end = hits[idx + 1][0] if idx + 1 < len(hits) else len(lines)
        body = "\n".join(lines[start:end])
        # 匹配章节 key
        key = None
        for k, kws in SECTION_KEYWORDS:
            if any(kw in title for kw in kws):
                key = k
                break
        if key is None:
            safe_title = re.sub(r"[^\w一-龥]", "_", title)[:20]
            key = f"sec_{idx}_{safe_title}"
        sections[key] = (start, end, body)
        order.append((key, title, start))
    # preamble = 第一条 \section 之前
    preamble_end = hits[0][0] if hits else len(lines)
    sections["preamble"] = (0, preamble_end, "\n".join(lines[0:preamble_end]))
    return sections, order


def has_chinese(s: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in s)


# --------------------------------------------------------------------------- #
# 各机检规则
# --------------------------------------------------------------------------- #
def _sec_body(ctx: PaperContext, key: str) -> str:
    body = ctx.sections.get(key, (0, 0, ""))[2]
    # 兜底：参考文献章节若未用 \section{参考文献}，退化为 thebibliography 环境
    if key == "ref" and not body:
        m = re.search(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
                      ctx.tex_text, re.S)
        if m:
            body = m.group(0)
    return body


def _abstract_body(ctx: PaperContext) -> tuple[str, bool]:
    """Return ``(body, is_production_environment)`` with legacy fallback."""
    active = _document_body_from_active_source(_active_tex_source(ctx.tex_text))
    match = re.search(
        r"\\begin\s*\{abstract\}(.*?)\\end\s*\{abstract\}",
        active,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1), True
    return _sec_body(ctx, "abstract"), False


_CHINESE_QUESTION_NUMBERS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def _question_numbers(text: str) -> set[int]:
    pattern = re.compile(
        r"问题\s*(?:(?P<problem_cn>[一二三四五六七八九十]+)|(?P<problem_digit>\d+))|"
        r"第\s*(?:(?P<ordinal_cn>[一二三四五六七八九十]+)|(?P<ordinal_digit>\d+))\s*问|"
        r"(?<![A-Za-z0-9_])(?:Q|Question)\s*(?P<latin>\d+)(?!\d)",
        re.IGNORECASE,
    )
    numbers: set[int] = set()
    for match in pattern.finditer(text):
        raw = (
            match.group("problem_digit")
            or match.group("ordinal_digit")
            or match.group("latin")
        )
        if raw is not None:
            numbers.add(int(raw))
            continue
        chinese = match.group("problem_cn") or match.group("ordinal_cn")
        value = _CHINESE_QUESTION_NUMBERS.get(chinese or "")
        if value is None and chinese and "十" in chinese:
            tens, ones = chinese.split("十", 1)
            tens_value = _CHINESE_QUESTION_NUMBERS.get(tens, 1) if tens else 1
            ones_value = _CHINESE_QUESTION_NUMBERS.get(ones, 0) if ones else 0
            value = tens_value * 10 + ones_value
        if value is not None:
            numbers.add(value)
    return numbers


def _keyword_tokens(value: str) -> tuple[list[str], list[str]]:
    raw_tokens = re.split(r"\\(?:quad|qquad)(?![A-Za-z@])|[；;，,]", value)
    normalized: list[str] = []
    display: list[str] = []
    for raw in raw_tokens:
        token = raw.strip()
        if not token:
            continue
        plain = token
        previous = None
        while previous != plain:
            previous = plain
            plain = re.sub(
                r"\\(?:mbox|textbf|textit|textrm|mathrm)\s*\{([^{}]*)\}",
                r"\1",
                plain,
                flags=re.IGNORECASE,
            )
        for escaped, literal in ((r"\&", "&"), (r"\%", "%"), (r"\_", "_")):
            plain = plain.replace(escaped, literal)
        plain = re.sub(r"\\[A-Za-z@]+\*?", "", plain)
        plain = re.sub(r"[{}~\s]+", "", plain)
        plain = unicodedata.normalize("NFKC", plain).casefold()
        if plain:
            normalized.append(plain)
            display.append(token)
    return normalized, display


def _keyword_value(body: str, production: bool) -> tuple[str | None, str | None]:
    commands = list(re.finditer(r"\\keywords\b", body, re.IGNORECASE))
    if commands:
        if len(commands) != 1:
            return None, "摘要中必须且只能出现一个 \\keywords{...}"
        value, _ = _read_braced_argument(body, commands[0].end())
        if value is None or not value.strip():
            return None, "\\keywords{...} 必须花括号闭合且内容非空"
        return value, None
    if production:
        return None, "生产摘要环境缺少非空的 \\keywords{...}"
    plain = re.search(r"关键词\s*[:：]\s*([^\r\n]+)", body, re.IGNORECASE)
    if plain is None or not plain.group(1).strip():
        return None, "摘要未发现非空关键词行"
    return plain.group(1), None


def check_q03(ctx: PaperContext) -> CheckResult:
    """Q03 中文论文的图题至少包含中文；标准缩写/变量可保留。"""
    if not ctx.tex_text:
        return CheckResult("Q03", "pending", TEX_ONLY_PENDING)
    active = _active_tex_source(ctx.tex_text)
    if "UNRESOLVED_TEX_CONDITIONAL" in active:
        return CheckResult("Q03", "fail", "存在无法静态判定的 TeX 条件分支")
    clean = _document_body_from_active_source(active)
    captions = [
        caption for caption in _caption_texts(clean)
        if "#" not in caption
    ]
    captions.extend(
        figure["caption"]
        for figure in _large_figure_spans(clean, _figure_wrapper_specs(active))
        if figure["kind"].lower() not in {"figure", "figure*"}
        and figure["caption"]
    )
    bad = [c for c in captions if not has_chinese(c)]
    if bad:
        return CheckResult("Q03", "fail", f"{len(bad)} 个题注纯 ASCII，如：{bad[0][:40]}")
    return CheckResult("Q03", "pass", f"全部 {len(captions)} 个 caption 均含中文说明")


def check_q04(ctx: PaperContext) -> CheckResult:
    """Q04 每个图/表都在正文被引用。对账 label/ref 与 caption 编号。"""
    if not ctx.tex_text:
        return CheckResult("Q04", "pending", TEX_ONLY_PENDING)
    active = _active_tex_source(ctx.tex_text)
    if "UNRESOLVED_TEX_CONDITIONAL" in active:
        return CheckResult("Q04", "fail", "存在无法静态判定的 TeX 条件分支")
    clean = _document_body_from_active_source(active)
    float_re = re.compile(
        r"\\begin\s*\{(?P<env>figure\*?|table\*?|longtable)\}"
        r"(?P<body>.*?)\\end\s*\{(?P=env)\}",
        re.I | re.S,
    )
    floats = list(float_re.finditer(clean))
    failures = []
    all_bound_labels = []
    checked = 0
    for match in floats:
        body = match.group("body")
        block_labels = re.findall(r"\\label\s*\{([^}]+)\}", body)
        if any("#" in label for label in block_labels):
            continue
        checked += 1
        has_caption = bool(re.search(r"\\caption(?:\[[^]]*\])?\s*\{", body, re.S))
        labels = [label.strip() for label in block_labels if label.strip()]
        if not has_caption:
            failures.append(f"第 {checked} 个 {match.group('env')} 缺少 caption")
        if not labels:
            failures.append(f"第 {checked} 个 {match.group('env')} 缺少 label")
        else:
            label = labels[-1]
            if not re.search(
                rf"\\(?:ref|autoref)\s*\{{{re.escape(label)}\}}",
                clean[:match.start()],
                re.I,
            ):
                failures.append(
                    f"第 {checked} 个 {match.group('env')} 的主 label 未在图表前被 ref 引用：{label}"
                )
            all_bound_labels.append(label)

    for figure in _large_figure_spans(clean, _figure_wrapper_specs(active)):
        if figure["kind"].lower() in {"figure", "figure*"}:
            continue
        checked += 1
        caption = figure["caption"]
        label = figure["bound_label"]
        if not caption:
            failures.append(f"第 {checked} 个 {figure['kind']} 调用缺少题注")
        if not label:
            failures.append(f"第 {checked} 个 {figure['kind']} 调用缺少 label")
        elif not re.search(
            rf"\\(?:ref|autoref)\s*\{{{re.escape(label)}\}}",
            clean[:figure["start"]],
            re.I,
        ):
            failures.append(
                f"第 {checked} 个 {figure['kind']} 的 label 未在图前被 ref 引用：{label}"
            )
        if label:
            all_bound_labels.append(label)
    duplicate_labels = sorted(
        {label for label in all_bound_labels if all_bound_labels.count(label) > 1}
    )
    if duplicate_labels:
        failures.append(f"图表 label 重复：{duplicate_labels}")
    if failures:
        return CheckResult("Q04", "fail", "；".join(failures))
    return CheckResult("Q04", "pass", f"{checked} 个图表均有 caption、唯一 label 与图表前正文引用")


def check_s03_s04(ctx: PaperContext) -> tuple[CheckResult, CheckResult]:
    """S03/S04 share the release audit's main-symbol table contract."""
    if not ctx.tex_text:
        return (
            CheckResult("S03", "pending", TEX_ONLY_PENDING),
            CheckResult("S04", "pending", TEX_ONLY_PENDING),
        )
    analysis = analyze_symbol_glossary(ctx.tex_text)
    expansion_errors = ctx.tex_expansion_errors
    if expansion_errors:
        detail = "TeX 展开失败：" + "；".join(expansion_errors[:3])
        return (CheckResult("S03", "fail", detail), CheckResult("S04", "fail", detail))

    if analysis["structure_ok"]:
        s03 = CheckResult(
            "S03",
            "pass",
            f"主要符号三线表结构合规，共 {analysis['data_row_count']} 条真实数据行",
        )
    else:
        s03 = CheckResult(
            "S03",
            "fail",
            "；".join(analysis["structure_failures"]),
        )
    if analysis["metadata_ok"]:
        s04 = CheckResult("S04", "pass", "符号表题注、唯一 label 与表前正文引用完整")
    else:
        s04 = CheckResult(
            "S04",
            "fail",
            "；".join(analysis["metadata_failures"]),
        )
    return s03, s04


def check_a_series(ctx: PaperContext) -> list[CheckResult]:
    if not ctx.tex_text:
        return [
            CheckResult("A02", "pending", TEX_ONLY_PENDING),
            CheckResult("A10", "pending", TEX_ONLY_PENDING),
        ]
    body, production = _abstract_body(ctx)
    if not body:
        return [
            CheckResult("A02", "pending", "未找到摘要章节"),
            CheckResult("A10", "pending", "未找到摘要章节"),
        ]
    # A02: 提供题目数量时必须逐问覆盖；不限定“针对问题#”固定句式。
    found = _question_numbers(body)
    if isinstance(ctx.problems, int) and not isinstance(ctx.problems, bool) and ctx.problems > 0:
        missing = sorted(set(range(1, ctx.problems + 1)) - found)
        if missing:
            a02 = CheckResult(
                "A02",
                "fail",
                "摘要缺少问题编号：" + "、".join(map(str, missing))
                + "；已识别：" + ("、".join(map(str, sorted(found))) or "无"),
            )
        else:
            a02 = CheckResult(
                "A02",
                "pass",
                f"摘要已覆盖问题 1–{ctx.problems}",
            )
    else:
        a02 = CheckResult("A02", "pass", "摘要内能识别问题编号") if found \
            else CheckResult("A02", "fail", "摘要未发现可识别的问题编号")

    # A10: 仅检查关键词行的结构、数量和重复；领域覆盖仍由人工判断。
    keyword_value, keyword_error = _keyword_value(body, production)
    if keyword_error:
        a10 = CheckResult("A10", "fail", keyword_error)
    else:
        normalized, display = _keyword_tokens(keyword_value or "")
        duplicates = sorted({
            display[index]
            for index, value in enumerate(normalized)
            if normalized.count(value) > 1
        })
        if duplicates:
            a10 = CheckResult(
                "A10",
                "fail",
                "关键词存在重复项：" + "、".join(duplicates),
            )
        elif not 3 <= len(normalized) <= 6:
            a10 = CheckResult(
                "A10",
                "fail",
                f"关键词共 {len(normalized)} 个，内部结构规则要求 3–6 个",
            )
        else:
            a10 = CheckResult(
                "A10",
                "pass",
                f"关键词共 {len(normalized)} 个，均非空且无重复；领域覆盖仍需人工判断",
            )
    return [a02, a10]


def check_v_series(ctx: PaperContext) -> list[CheckResult]:
    if not ctx.tex_text:
        return [CheckResult(f"V0{i}", "pending", TEX_ONLY_PENDING) for i in range(1, 5)]
    if not ctx.archetype:
        return [CheckResult(f"V0{i}", "pending", "未提供 --archetype") for i in range(1, 5)]
    # 检验内容常嵌在编号问题的 subsection/subsubsection 中，而非独立 section。
    # 未切出独立检验章时审查展开后的全文，避免把真实灵敏度/误差证据误判为空。
    body = _sec_body(ctx, "check") or ctx.tex_text
    results = []
    # V01 评价类：至少出现稳定性/敏感性/一致性/外部对照证据之一。
    if ctx.archetype == "evaluation":
        if re.search(r"权重.*(?:敏感|稳定)|排序.*稳定|一致性|外部对照|稳健性", body, re.S):
            results.append(CheckResult("V01", "pass", "评价类含权重/排序稳定性、一致性或外部对照证据"))
        else:
            results.append(CheckResult("V01", "fail", "评价类未发现权重/排序稳定性、一致性或外部对照证据"))
    else:
        results.append(CheckResult("V01", "na", "非评价类，本条不适用"))
    # V02 分类：准确率可能误导不平衡任务，优先检查诊断性指标。
    if ctx.archetype == "classification-cv":
        if re.search(r"混淆矩阵|精确率|召回率|F1|precision|recall", body, re.I):
            results.append(CheckResult("V02", "pass", "分类检验含混淆矩阵、P/R 或 F1 证据"))
        else:
            results.append(CheckResult("V02", "fail", "分类检验未发现混淆矩阵、P/R 或 F1 证据"))
    else:
        results.append(CheckResult("V02", "na", "非分类类，本条不适用"))
    # V03 预测：误差
    if ctx.archetype == "prediction":
        if re.search(r"误差|RMSE|MAE|MAPE", body):
            results.append(CheckResult("V03", "pass", "检验章节含“误差/RMSE/MAE/MAPE”"))
        else:
            results.append(CheckResult("V03", "fail", "预测类检验章节未发现“误差”"))
    else:
        results.append(CheckResult("V03", "na", "非预测类，本条不适用"))
    # V04 优化：可行性、收敛、最优性边界或灵敏度均可构成适配证据。
    if ctx.archetype == "optimization":
        if re.search(r"可行(?:性|解)|约束.*满足|收敛|最优性|上下界|误差界|灵敏度|sensitivity", body, re.I | re.S):
            results.append(CheckResult("V04", "pass", "优化检验含可行性、收敛、边界或灵敏度证据"))
        else:
            results.append(CheckResult("V04", "fail", "优化检验未发现可行性、收敛、边界或灵敏度证据"))
    else:
        results.append(CheckResult("V04", "na", "非优化类，本条不适用"))
    return results


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def run_machine_checks(ctx: PaperContext) -> dict[str, CheckResult]:
    out: dict[str, CheckResult] = {}
    out["Q03"] = check_q03(ctx)
    out["Q04"] = check_q04(ctx)
    s03, s04 = check_s03_s04(ctx)
    out["S03"], out["S04"] = s03, s04
    for r in check_a_series(ctx):
        out[r.item_id] = r
    for r in check_v_series(ctx):
        out[r.item_id] = r
    return out


def load_decisions(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_decisions(path: Path, decisions: dict) -> None:
    path.write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")


def decision_errors(decisions: dict, checklist: dict) -> list[str]:
    """Reject unknown/machine overrides and unexplained NA decisions."""
    if not isinstance(decisions, dict):
        return ["裁决文件必须是 JSON 对象"]
    manual_ids = {
        item["id"] for item in checklist["items"]
        if item["check_method"] == "manual"
    }
    known_ids = {item["id"] for item in checklist["items"]}
    errors = []
    for item_id, decision in decisions.items():
        if item_id not in known_ids:
            errors.append(f"未知自检项：{item_id}")
            continue
        if item_id not in manual_ids:
            errors.append(f"机检项不得用 sidecar 覆盖：{item_id}")
            continue
        if not isinstance(decision, dict) or decision.get("status") not in {"pass", "na"}:
            errors.append(f"{item_id} 的裁决必须为 pass 或 na")
            continue
        note = str(decision.get("note", "")).strip()
        if decision["status"] == "na" and len(note) < 4:
            errors.append(f"{item_id}=na 必须给出具体理由（至少 4 个字符）")
    return errors


def render_report(checklist: dict, results: dict[str, CheckResult],
                  ctx: PaperContext) -> str:
    lines = ["# 论文自检表_已勾选", ""]
    paper_path = ctx.tex_path or ctx.docx_path
    try:
        display_path = paper_path.relative_to(Path.cwd()) if paper_path else ""
    except ValueError:
        display_path = paper_path.name if paper_path else ""
    lines.append(f"- 论文: `{display_path}`")
    if ctx.problems is not None:
        lines.append(f"- 问题数: {ctx.problems}")
    if ctx.archetype:
        lines.append(f"- 题型: {ctx.archetype}")
    lines.append("")
    cur_section = None
    n_pass = n_fail = n_pending = n_na = 0
    for item in checklist["items"]:
        sid = item["id"]
        sec = item["section"]
        if sec != cur_section:
            lines.append(f"\n## {sec}\n")
            cur_section = sec
        r = results.get(sid)
        if r is None:
            # 人工条目：看 sidecar
            dec = ctx.decisions.get(sid)
            if dec and dec.get("status") == "pass":
                icon = "✅"
                note = dec.get("note", "")
                n_pass += 1
            elif dec and dec.get("status") == "na":
                icon = "➖"
                note = "不适用：" + dec.get("note", "")
                n_na += 1
            else:
                icon = "☐"
                note = "待人工：" + item["item"]
                n_pending += 1
        else:
            if r.status == "pass":
                icon = "✅"
                n_pass += 1
            elif r.status == "fail":
                icon = "❌"
                n_fail += 1
            elif r.status == "na":
                icon = "➖"
                n_na += 1
            else:
                icon = "☐"
                n_pending += 1
            note = r.evidence or r.detail
        line = f"- {icon} **{sid}** {item['item']}"
        if note:
            line += f"  — {note}"
        if item.get("notes"):
            line += f"  【注：{item['notes']}】"
        lines.append(line)
    lines.append("")
    lines.append("---")
    lines.append(f"统计：✅ {n_pass}  ❌ {n_fail}  ☐ {n_pending}  ➖ {n_na}")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    # Redirected Windows streams may default to GBK, which cannot encode
    # checklist markers such as “☐”. Keep console output aligned with the
    # UTF-8 report file instead of crashing after the report is generated.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="优秀论文自检表机检（Wave6-A）。")
    ap.add_argument("--tex", help="输入 .tex 论文路径")
    ap.add_argument("--docx", help="输入 .docx 论文路径（尽力做）")
    ap.add_argument("--problems", type=int, default=None, help="问题数量")
    ap.add_argument("--archetype", default=None, choices=sorted(ARCHETYPES),
                    help="题型，用于 V01-V04 检查")
    ap.add_argument("--outdir", default=None, help="输出目录（默认论文所在目录）")
    ap.add_argument("--mark", action="append", default=[],
                    help="记录人工裁决 ID=pass|na，可多次")
    ap.add_argument("--note", default="", help="配合 --mark 的备注")
    ap.add_argument("--strict", action="store_true",
                    help="任何机检 fail/pending 或人工条目未裁决即失败")
    args = ap.parse_args(argv)

    if not args.tex and not args.docx and not args.mark:
        ap.print_help()
        if args.strict:
            print("\n[FAIL] --strict 必须同时提供 --tex 或 --docx。", file=sys.stderr)
            return 2
        return 0

    tex_path = Path(args.tex).resolve() if args.tex else None
    docx_path = Path(args.docx).resolve() if args.docx else None
    outdir = Path(args.outdir).resolve() if args.outdir else (
        tex_path.parent if tex_path else (docx_path.parent if docx_path else Path.cwd()))
    outdir.mkdir(parents=True, exist_ok=True)
    decisions_path = outdir / DECISIONS_NAME

    checklist = load_checklist()

    # --mark 模式：只写 sidecar
    if args.mark:
        decisions = load_decisions(decisions_path)
        existing_errors = decision_errors(decisions, checklist)
        if existing_errors:
            print("裁决文件无效：" + "；".join(existing_errors), file=sys.stderr)
            return 2
        for spec in args.mark:
            if "=" not in spec:
                print(f"--mark 格式错误：{spec}，应为 ID=pass|na", file=sys.stderr)
                return 2
            sid, val = spec.split("=", 1)
            sid, val = sid.strip(), val.strip().lower()
            if val not in ("pass", "na"):
                print(f"--mark 取值必须是 pass|na：{spec}", file=sys.stderr)
                return 2
            decisions[sid] = {"status": val, "note": args.note}
        new_errors = decision_errors(decisions, checklist)
        if new_errors:
            print("裁决无效：" + "；".join(new_errors), file=sys.stderr)
            return 2
        save_decisions(decisions_path, decisions)
        print(f"已记录 {len(args.mark)} 条人工裁决 -> {decisions_path}")
        return 0

    # 跑机检
    decisions = load_decisions(decisions_path)
    existing_errors = decision_errors(decisions, checklist)
    if existing_errors:
        print("裁决文件无效：" + "；".join(existing_errors), file=sys.stderr)
        return 2
    ctx = PaperContext(tex_path=tex_path, docx_path=docx_path,
                       problems=args.problems, archetype=args.archetype,
                       decisions=decisions)
    if tex_path and tex_path.exists():
        project_root = find_project_root(tex_path.parent)
        ctx.tex_text, ctx.tex_expansion_errors = expand_tex_in_order(
            tex_path,
            project_root,
            base=tex_path.parent,
        )
        ctx.tex_lines = ctx.tex_text.splitlines()
        ctx.sections, _ = split_sections(ctx.tex_text)
    else:
        print(
            f"[warn] 未找到可读 tex：{tex_path}；依赖 TeX 的机检条目将 pending。"
            "DOCX 请另运行 scripts/audit_docx.py。",
            file=sys.stderr,
        )

    results = run_machine_checks(ctx)
    report = render_report(checklist, results, ctx)
    report_path = outdir / REPORT_NAME
    status_map = {
        item_id.strip(): icon
        for icon, item_id in re.findall(
            r"^-\s*(✅|❌|☐|➖)\s*\*\*([^*]+)\*\*",
            report,
            re.MULTILINE,
        )
    }
    paper_path = tex_path or docx_path
    provenance = build_provenance(
        paper_path,
        outdir,
        decisions_path,
        status_map,
        args.problems,
        args.archetype,
    )
    provenance_line = json.dumps(
        provenance, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    report = report.replace(
        "# 论文自检表_已勾选\n",
        f"# 论文自检表_已勾选\n\n<!-- paper-checklist-provenance: {provenance_line} -->\n",
        1,
    )
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n报告已写入: {report_path}")

    # 退出码
    n_fail = sum(1 for r in results.values() if r.status == "fail")
    strict_blocked = False
    if args.strict:
        machine_pending = sorted(
            item_id for item_id, result in results.items() if result.status == "pending"
        )
        if machine_pending:
            print(
                f"[strict] 仍有 {len(machine_pending)} 条机检项目处于 pending："
                + ", ".join(machine_pending),
                file=sys.stderr,
            )
            strict_blocked = True
        # 人工条目未裁决：统计 checklist 中 manual 且未在 decisions 里的
        manual_unresolved = 0
        for item in checklist["items"]:
            if item["check_method"] != "manual":
                continue
            sid = item["id"]
            if sid in ctx.decisions:
                continue
            # 机检结果里若已给 pass/fail/na 则不算未裁决
            r = results.get(sid)
            if r is None or r.status == "pending":
                manual_unresolved += 1
        if manual_unresolved:
            print(f"[strict] 仍有 {manual_unresolved} 条人工条目未裁决", file=sys.stderr)
            strict_blocked = True
    if strict_blocked:
        return 1
    if n_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
