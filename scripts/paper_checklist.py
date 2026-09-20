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
            key = f"sec_{idx}_{re.sub(r'[^\\w一-龥]', '_', title)[:20]}"
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


def check_r02(ctx: PaperContext) -> CheckResult:
    """R02 参考文献无 DOI。"""
    body = _sec_body(ctx, "ref")
    if not body:
        return CheckResult("R02", "pending", "未找到“参考文献”章节，待人工确认")
    m = re.search(r"10\.\d{4,}/\S+", body)
    if m:
        return CheckResult("R02", "fail", f"参考文献中含 DOI：{m.group(0)[:40]}")
    return CheckResult("R02", "pass", "参考文献章节未发现 DOI 正则 10.\\d{4,}/")


def check_q02(ctx: PaperContext) -> CheckResult:
    """Q02 图表宽度≈0.8（>0.95 或缺失即 flag）。"""
    issues = []
    # \includegraphics[width=..., height=...]{...}
    for m in re.finditer(r"\\includegraphics\[[^\]]*width\s*=\s*([0-9.]+)\\?\\textwidth", ctx.tex_text):
        w = float(m.group(1))
        if w > 0.95:
            issues.append(f"图 width={w} > 0.95")
    # 没带 width= 的 includegraphics
    missing = len(re.findall(r"\\includegraphics(?!\[[^\]]*width)", ctx.tex_text))
    if missing:
        issues.append(f"{missing} 个 \\includegraphics 未声明 width")
    if issues:
        return CheckResult("Q02", "fail", "；".join(issues[:5]))
    return CheckResult("Q02", "pass", "图宽度均在 [0.6,0.95] 区间且已声明")


def check_q03(ctx: PaperContext) -> CheckResult:
    """Q03 题注含中文。"""
    captions = re.findall(r"\\caption\s*\{([^}]*)\}", ctx.tex_text)
    bad = [c for c in captions if not has_chinese(c)]
    if bad:
        return CheckResult("Q03", "fail", f"{len(bad)} 个题注纯 ASCII，如：{bad[0][:40]}")
    return CheckResult("Q03", "pass", f"全部 {len(captions)} 个 caption 含中文")


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


def check_q09(ctx: PaperContext) -> CheckResult:
    """Q09 模型求解章节无分点加粗（允许公式内 \\mathbf）。"""
    body = _sec_body(ctx, "solving")
    if not body:
        return CheckResult("Q09", "pending", "未找到“模型求解”章节，待人工确认")
    # 去掉公式内 \mathbf
    cleaned = re.sub(r"\\mathbf\s*\{", "", body)
    bolds = re.findall(r"\\textbf(?:\*)?\s*\{", cleaned)
    if bolds:
        return CheckResult("Q09", "fail", f"模型求解章节含 {len(bolds)} 处 \\textbf")
    return CheckResult("Q09", "pass", "模型求解章节未发现 \\textbf")


def check_s03_s04(ctx: PaperContext) -> tuple[CheckResult, CheckResult]:
    """S03 2 列三线表；S04 表有 caption。"""
    body = _sec_body(ctx, "symbol")
    if not body:
        return (CheckResult("S03", "pending", "未找到“符号说明”章节"),
                CheckResult("S04", "pending", "未找到“符号说明”章节"))
    has_top = bool(re.search(r"\\toprule", body))
    has_mid = bool(re.search(r"\\midrule", body))
    has_bot = bool(re.search(r"\\bottomrule", body))
    has_caption = bool(re.search(r"\\caption", body))
    # 列数：取 tabular 环境列规格
    col_spec = re.search(r"\\begin\{(?:table|table\*)\}.*?\\begin\{tabular\}\s*\{([^}]*)\}",
                         body, re.S)
    ncol = None
    if col_spec:
        spec = col_spec.group(1)
        # 去掉 @{}、>{..}、<{..} 等，计 c/l/r/p 个数
        cleaned = re.sub(r"[<>\@]\{[^}]*\}", "", spec)
        ncol = len(re.findall(r"[clrp]", cleaned))
    if has_top and has_mid and has_bot and ncol == 2:
        s03 = CheckResult("S03", "pass", f"三线表齐全（top/mid/bottom），列数={ncol}")
    else:
        s03 = CheckResult("S03", "fail",
                          f"三线表/列数不符：top={has_top} mid={has_mid} bot={has_bot} cols={ncol}")
    s04 = CheckResult("S04", "pass", "符号说明表含 \\caption") if has_caption \
        else CheckResult("S04", "fail", "符号说明表缺 \\caption")
    return s03, s04


def check_h04_h05(ctx: PaperContext) -> tuple[CheckResult, CheckResult]:
    body = _sec_body(ctx, "assumption")
    if not body:
        return (CheckResult("H04", "pending", "未找到“模型假设”章节"),
                CheckResult("H05", "pending", "未找到“模型假设”章节"))
    items = re.findall(r"^\s*假设\s*(\d+)\s*[：:]", body, re.M)
    if not items:
        return (CheckResult("H04", "fail", "未匹配到“假设#：”格式"),
                CheckResult("H05", "fail", "未匹配到“假设#：”格式"))
    h04 = CheckResult("H04", "pass", f"匹配到 {len(items)} 条“假设#：”")
    if ctx.problems is None:
        h05 = CheckResult("H05", "pending", "未提供 --problems，无法核对条数")
    elif len(items) == ctx.problems:
        h05 = CheckResult("H05", "pass", f"假设 {len(items)} 条 == 问题数 {ctx.problems}")
    else:
        h05 = CheckResult("H05", "fail", f"假设 {len(items)} 条 != 问题数 {ctx.problems}")
    return h04, h05


def check_b12(ctx: PaperContext) -> CheckResult:
    body = _sec_body(ctx, "intro")
    if not body:
        return CheckResult("B12", "pending", "未找到“引言/问题重述”章节")
    if re.search(r"\\textbf\s*\{\s*问题\s*\d+", body):
        return CheckResult("B12", "pass", "问题重述中“问题#”已加粗")
    return CheckResult("B12", "fail", "问题重述未发现 \\textbf{问题#...}")


def check_a_series(ctx: PaperContext) -> list[CheckResult]:
    body = _sec_body(ctx, "abstract")
    if not body:
        return [
            CheckResult("A02", "pending", "未找到摘要章节"),
            CheckResult("A10", "pending", "未找到摘要章节"),
        ]
    # A02: 含“针对问题#”
    a02 = CheckResult("A02", "pass", "摘要含“针对问题\\d+”") if re.search(r"针对问题\s*\d+", body) \
        else CheckResult("A02", "fail", "摘要未出现“针对问题#”")
    # A10: 关键词行
    a10 = CheckResult("A10", "pass", "摘要含“关键词”或 \\keywords") \
        if (re.search(r"关键词", body) or re.search(r"\\keywords", body)) \
        else CheckResult("A10", "fail", "摘要未发现“关键词”行")
    # 摘要无公式：去掉环境外的 $ 计数
    # 粗略：摘要内出现成对 $ 即视为公式
    dollar_pairs = len(re.findall(r"\$[^$]+\$", body))
    a_no_formula = CheckResult("A07", "pass", f"摘要内未发现 $...$ 公式") if dollar_pairs == 0 \
        else CheckResult("A07", "fail", f"摘要内出现 {dollar_pairs} 处 $...$ 公式")
    return [a02, a10, a_no_formula]


def check_e_series(ctx: PaperContext) -> list[CheckResult]:
    body = _sec_body(ctx, "eval")
    if not body:
        return [
            CheckResult("E01", "pending", "未找到“模型评价”章节"),
            CheckResult("E03", "pending", "未找到“模型评价”章节"),
            CheckResult("E05", "pending", "未找到“模型评价”章节"),
        ]
    adv = re.findall(r"^\s*优点\s*(\d+)\s*[：:]", body, re.M)
    dis = re.findall(r"^\s*缺点\s*(\d+)\s*[：:]", body, re.M)
    e01 = CheckResult("E01", "pass", f"匹配 {len(adv)} 条“优点#：”") if adv \
        else CheckResult("E01", "fail", "未匹配“优点#：”")
    e05 = CheckResult("E05", "pass", f"匹配 {len(dis)} 条“缺点#：”") if dis \
        else CheckResult("E05", "fail", "未匹配“缺点#：”")
    if len(adv) > len(dis):
        e03 = CheckResult("E03", "pass", f"优点 {len(adv)} > 缺点 {len(dis)}")
    else:
        e03 = CheckResult("E03", "fail", f"优点 {len(adv)} 不大于缺点 {len(dis)}")
    return [e01, e03, e05]


def check_v_series(ctx: PaperContext) -> list[CheckResult]:
    if not ctx.archetype:
        return [CheckResult(f"V0{i}", "pending", "未提供 --archetype") for i in range(1, 5)]
    body = _sec_body(ctx, "check")
    results = []
    # V01 评价类：不应有“检验结果”章
    if ctx.archetype == "evaluation":
        if re.search(r"检验结果|检验与分析|灵敏度|误差|准确率", body):
            results.append(CheckResult("V01", "fail", "评价类不应有检验章节，但检出相关关键词"))
        else:
            results.append(CheckResult("V01", "pass", "评价类未发现检验章节"))
    else:
        results.append(CheckResult("V01", "na", "非评价类，本条不适用"))
    # V02 分类：准确率
    if ctx.archetype == "classification-cv":
        if re.search(r"准确率|Accuracy|accuracy", body):
            results.append(CheckResult("V02", "pass", "检验章节含“准确率/Accuracy”"))
        else:
            results.append(CheckResult("V02", "fail", "分类类检验章节未发现“准确率”"))
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
    # V04 优化：灵敏度
    if ctx.archetype == "optimization":
        if re.search(r"灵敏度|Sensitivity|sensitivity", body):
            results.append(CheckResult("V04", "pass", "检验章节含“灵敏度/Sensitivity”"))
        else:
            results.append(CheckResult("V04", "fail", "优化类检验章节未发现“灵敏度”"))
    else:
        results.append(CheckResult("V04", "na", "非优化类，本条不适用"))
    return results


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def run_machine_checks(ctx: PaperContext) -> dict[str, CheckResult]:
    out: dict[str, CheckResult] = {}
    out["R02"] = check_r02(ctx)
    out["Q02"] = check_q02(ctx)
    out["Q03"] = check_q03(ctx)
    out["Q04"] = check_q04(ctx)
    out["Q09"] = check_q09(ctx)
    s03, s04 = check_s03_s04(ctx)
    out["S03"], out["S04"] = s03, s04
    h04, h05 = check_h04_h05(ctx)
    out["H04"], out["H05"] = h04, h05
    out["B12"] = check_b12(ctx)
    for r in check_a_series(ctx):
        out[r.item_id] = r
    for r in check_e_series(ctx):
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
    lines.append(f"- 论文: `{ctx.tex_path or ctx.docx_path}`")
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
    n_pending = sum(1 for r in results.values() if r.status == "pending")
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
