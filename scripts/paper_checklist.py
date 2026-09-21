#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_checklist.py — 优秀论文自检表机检脚本（Wave6-A）。

对 .tex（必做）/ .docx（尽力做）论文运行 138 条自检表中可确定性检查的条目，
输出 Markdown 报告，并在论文目录生成《论文自检表_已勾选.md》。

人工条目（字体、配色、叙事流畅度等）输出 ☐ 待人工；用 --mark ID=pass|na 记录裁决，
持久化到论文目录旁的 paper_checklist_decisions.json。--strict 模式下未裁决人工条目即失败。

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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKLIST_JSON = REPO_ROOT / "assets" / "checklists" / "paper_checklist.json"
DECISIONS_NAME = "paper_checklist_decisions.json"
REPORT_NAME = "论文自检表_已勾选.md"

ARCHETYPES = {
    "optimization", "evaluation", "prediction", "classification-cv",
    "mechanism", "signal", "spatial-graph", "simulation",
}

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


def check_q03(ctx: PaperContext) -> CheckResult:
    """Q03 中文论文的图题至少包含中文；标准缩写/变量可保留。"""
    captions = re.findall(r"\\caption\s*\{([^}]*)\}", ctx.tex_text)
    bad = [c for c in captions if not has_chinese(c)]
    if bad:
        return CheckResult("Q03", "fail", f"{len(bad)} 个题注纯 ASCII，如：{bad[0][:40]}")
    return CheckResult("Q03", "pass", f"全部 {len(captions)} 个 caption 均含中文说明")


def check_q04(ctx: PaperContext) -> CheckResult:
    """Q04 每个图/表都在正文被引用。对账 label/ref 与 caption 编号。"""
    # 收集所有 \label{...} 与 \ref{...}
    labels = set(re.findall(r"\\label\s*\{([^}]+)\}", ctx.tex_text))
    refs = set(re.findall(r"\\(?:ref|eqref|autoreval|autoref)\s*\{([^}]+)\}", ctx.tex_text))
    unreferenced = sorted(labels - refs)
    # 也兜底：caption 里的“图 N / 表 N”编号是否在正文出现（不含浮动体内）
    if unreferenced:
        return CheckResult("Q04", "fail", f"{len(unreferenced)} 个 label 未被 \\ref 引用：{unreferenced[:5]}")
    return CheckResult("Q04", "pass", f"{len(labels)} 个 label 全部被引用")


def check_s03_s04(ctx: PaperContext) -> tuple[CheckResult, CheckResult]:
    """S03 使用三线表（列数按内容决定）；S04 表有 caption。"""
    body = _sec_body(ctx, "symbol")
    if not body:
        return (CheckResult("S03", "pending", "未找到“符号说明”章节"),
                CheckResult("S04", "pending", "未找到“符号说明”章节"))
    has_top = bool(re.search(r"\\toprule", body))
    has_mid = bool(re.search(r"\\midrule", body))
    has_bot = bool(re.search(r"\\bottomrule", body))
    has_caption = bool(re.search(r"\\caption", body))
    if has_top and has_mid and has_bot:
        s03 = CheckResult("S03", "pass", "三线表命令齐全（top/mid/bottom），列数留待内容审查")
    else:
        s03 = CheckResult("S03", "fail", f"三线表命令不全：top={has_top} mid={has_mid} bot={has_bot}")
    s04 = CheckResult("S04", "pass", "符号说明表含 \\caption") if has_caption \
        else CheckResult("S04", "fail", "符号说明表缺 \\caption")
    return s03, s04


def check_a_series(ctx: PaperContext) -> list[CheckResult]:
    body = _sec_body(ctx, "abstract")
    if not body:
        return [
            CheckResult("A02", "pending", "未找到摘要章节"),
            CheckResult("A10", "pending", "未找到摘要章节"),
        ]
    # A02: 能识别问题编号，但不限定“针对问题#”固定句式。
    problem_mark = r"(?:问题\s*[一二三四五六七八九十\d]+|第\s*[一二三四五六七八九十\d]+\s*问)"
    a02 = CheckResult("A02", "pass", "摘要内能识别问题编号") if re.search(problem_mark, body) \
        else CheckResult("A02", "fail", "摘要未发现可识别的问题编号")
    # A10: 关键词行
    a10 = CheckResult("A10", "pass", "摘要含“关键词”或 \\keywords") \
        if (re.search(r"关键词", body) or re.search(r"\\keywords", body)) \
        else CheckResult("A10", "fail", "摘要未发现“关键词”行")
    return [a02, a10]


def check_v_series(ctx: PaperContext) -> list[CheckResult]:
    if not ctx.archetype:
        return [CheckResult(f"V0{i}", "pending", "未提供 --archetype") for i in range(1, 5)]
    body = _sec_body(ctx, "check")
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
                icon = "✅"; note = dec.get("note", "")
                n_pass += 1
            elif dec and dec.get("status") == "na":
                icon = "➖"; note = "不适用：" + dec.get("note", "")
                n_na += 1
            else:
                icon = "☐"; note = "待人工：" + item["item"]
                n_pending += 1
        else:
            if r.status == "pass":
                icon = "✅"; n_pass += 1
            elif r.status == "fail":
                icon = "❌"; n_fail += 1
            elif r.status == "na":
                icon = "➖"; n_na += 1
            else:
                icon = "☐"; n_pending += 1
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
                    help="存在未裁决人工条目即失败")
    args = ap.parse_args(argv)

    if not args.tex and not args.docx and not args.mark:
        ap.print_help()
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
        save_decisions(decisions_path, decisions)
        print(f"已记录 {len(args.mark)} 条人工裁决 -> {decisions_path}")
        return 0

    # 跑机检
    ctx = PaperContext(tex_path=tex_path, docx_path=docx_path,
                       problems=args.problems, archetype=args.archetype,
                       decisions=load_decisions(decisions_path))
    if tex_path and tex_path.exists():
        ctx.tex_text = tex_path.read_text(encoding="utf-8", errors="replace")
        ctx.tex_lines = ctx.tex_text.splitlines()
        ctx.sections, _ = split_sections(ctx.tex_text)
    else:
        print(f"[warn] 未找到 tex：{tex_path}，机检条目将全部 pending", file=sys.stderr)

    results = run_machine_checks(ctx)
    report = render_report(checklist, results, ctx)
    report_path = outdir / REPORT_NAME
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n报告已写入: {report_path}")

    # 退出码
    n_fail = sum(1 for r in results.values() if r.status == "fail")
    if args.strict:
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
            return 1
    if n_fail:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
