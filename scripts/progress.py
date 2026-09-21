#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""progress.py — P0–P6 进度与内容级门禁检查。

不是只查文件存在，而是查"内容达标"：
  - P1 读题审计 + 题型判定 + **用户确认记录**（无确认不得进入求解）
  - P2 模型假设必须 ≥3 条
  - P3 验证必须有 ≥1 种验证手段的结果文件
  - P4 论文必须有摘要/结论等章节
  - P5 终稿不得残留 TODO/占位符
空目录应 FAIL，完整目录应 PASS。

用法:
  python scripts/progress.py --root . --all
  python scripts/progress.py --root . --gate P2
  python scripts/progress.py --root . --gate P3 --json
"""
import argparse
import json
import re
import sys
from pathlib import Path

PHASES = ["P0", "P1", "P2", "P3", "P4", "P5", "P6"]


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        return ""


def _gather_text(root: Path, exts=(".md", ".tex", ".txt", ".docx")) -> str:
    """汇总论文/求解目录下文本文件内容（docx 跳过二进制）。"""
    chunks = []
    for sub in ("论文", "求解", "."):
        d = root / sub if sub != "." else root
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix in (".md", ".tex", ".txt"):
                chunks.append(_read_text(p))
    return "\n".join(chunks)


def count_assumptions(text: str) -> int:
    """粗略数模型假设条数：命中'假设'附近的编号/项目行。"""
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"^(\d+[\.、)]|（\d+）|\(\d+\)|[-*•])", s) and ("假设" in s or "假定" in s):
            n += 1
    # 兜底：出现"模型假设"小节再数其下编号行
    return n


def has_user_confirmation(root: Path) -> bool:
    """反 AI 读题审计硬门禁：必须存在用户确认记录，才允许进入求解。

    兼容两种落盘形式：
      1) evidence-ledger.json（根目录或 题目/ 下），其中 user_confirmation 为真
         （布尔 True，或字符串 "true"/"yes"/"已确认"）。
      2) evidence-ledger.md / reading_audit.md 中出现明确的用户确认标记
         （"用户已确认" / "确认通过" / "user_confirmation: true" 等）。
    无任何确认记录 → 返回 False（P1 不通过，禁止抢跑求解）。
    """
    # 1) JSON 台账
    for rel in ("evidence-ledger.json", "题目/evidence-ledger.json",
                "evidence_ledger.json", "题目/evidence_ledger.json"):
        p = root / rel
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8-sig", errors="ignore"))
            except Exception:
                continue
            val = data.get("user_confirmation")
            if val is True or str(val).strip().lower() in ("true", "yes", "已确认", "确认"):
                return True
    # 2) Markdown 台账 / 读题审计报告中的确认标记
    for rel in ("evidence-ledger.md", "题目/evidence-ledger.md",
                "题目/reading_audit.md", "reading_audit.md"):
        p = root / rel
        if not p.is_file():
            continue
        text = _read_text(p)
        if re.search(r"(用户已确认|确认通过|用户确认\s*[:：=]?\s*是|user_confirmation\s*[:：=]\s*true|裁决已记录)", text, re.I):
            return True
    return False


def has_validation_result(root: Path) -> bool:
    """是否存在验证结果文件/关键词。"""
    for pat in ("*验证*", "*validation*", "*对比*", "*sensitivity*", "*灵敏度*", "*消融*"):
        if list(root.rglob(pat)):
            return True
    text = _gather_text(root)
    return bool(re.search(r"(误差|RMSE|对比|灵敏度|鲁棒|消融|交叉验证|对标)", text))


# --- 优秀论文自检表门禁（Wave6-B）---

def _find_selfcheck(root: Path, names):
    """在比赛工作目录 论文/ 与根下查找自检表文件。"""
    for base in (root / "论文", root):
        for name in names:
            p = base / name
            if p.is_file():
                return p
    return None


def find_p4_checklist(root: Path):
    """P4：写作阶段的自检表（边写边勾）。"""
    return _find_selfcheck(root, (
        "优秀论文自检表.md", "论文自检表.md", "paper_checklist.md"))


def find_p6_checked(root: Path):
    """P6：已勾选自检表（100% 闭环产物）。"""
    return _find_selfcheck(root, (
        "论文自检表_已勾选.md", "优秀论文自检表_已勾选.md", "自检表_已勾选.md"))


def find_sidecar(root: Path):
    """P6：人工条目裁决 sidecar。"""
    return _find_selfcheck(root, ("paper_checklist_decisions.json",))


def count_undecided_decisions(sidecar: Path) -> int:
    """从 sidecar JSON 数未裁决人工条目。

    兼容多种落盘形态（Wave6-A 定 schema，此处防御式解析）：
      - {"pending": n} / {"summary": {"undecided": n}}
      - {"decisions":[{status:...}]} / {"items":[...]} / 顶层 list
    status 命中 (pending/undecided/todo/open/空/☐/none) 计为未裁决。
    无法解析返回 -1。
    """
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8-sig", errors="ignore"))
    except Exception:
        return -1

    def _is_und(r):
        if not isinstance(r, dict):
            return False
        st = str(r.get("status", r.get("decision", r.get("state", "")))).strip().lower()
        return st in ("", "pending", "undecided", "todo", "open", "none", "☐")

    if isinstance(data, dict):
        for k in ("pending", "undecided", "open", "todo"):
            if isinstance(data.get(k), int):
                return data[k]
        summ = data.get("summary")
        if isinstance(summ, dict):
            for k in ("undecided", "pending", "open"):
                if isinstance(summ.get(k), int):
                    return summ[k]
        recs = None
        for k in ("decisions", "items", "checklist", "results"):
            if isinstance(data.get(k), list):
                recs = data[k]
                break
        if recs is not None:
            return sum(1 for r in recs if _is_und(r))
    elif isinstance(data, list):
        return sum(1 for r in data if _is_und(r))
    return -1


def check_phase(phase: str, root: Path) -> tuple:
    """返回 (passed, [检查项])。每项 (ok, 描述)。"""
    items = []

    def need(cond, desc):
        items.append((bool(cond), desc))

    if phase == "P0":
        need(any((root / "题目").glob("*")) if (root / "题目").is_dir() else
             any(root.glob("*题*")) or any(root.glob("*.pdf")),
             "题面/题目文件已落盘")
        need((root / "config" / "contest.json").exists() or (root / "contest.json").exists(),
             "contest.json 存在")
        need(root.is_dir(), "工作目录存在")

    elif phase == "P1":
        text = _gather_text(root)
        need(re.search(r"约束|问题分析|拆解|直接目标", text), "有题面约束/问题拆解记录")
        need(re.search(r"原型|optimization|prediction|evaluation|匹配", text) or
             any(root.rglob("*match*")), "有题型/原型判定记录")
        need(has_user_confirmation(root), "反AI读题审计：存在用户确认记录（evidence-ledger user_confirmation=true）")

    elif phase == "P2":
        text = _gather_text(root)
        n = count_assumptions(text)
        need(n >= 3, f"模型假设 ≥3 条（检出 {n} 条）")
        need(re.search(r"目标函数|min|max|minimize|maximize", text, re.I), "有目标函数/模型链")
        need(any(root.rglob("*.m")) or any(root.rglob("*.py")), "有 baseline 求解脚本")

    elif phase == "P3":
        need(any(root.rglob("*.m")) or any(root.rglob("*.py")), "有求解代码")
        need(any(root.rglob("*.mat")) or any(root.rglob("*.csv")) or any(root.rglob("*.json")),
             "有结构化结果落盘")
        need(has_validation_result(root), "有 ≥1 种验证手段的结果/记录")

    elif phase == "P4":
        text = _gather_text(root)
        need(re.search(r"摘\s*要|Abstract", text), "论文含摘要")
        need(re.search(r"结论|总结", text), "论文含结论")
        need(re.search(r"模型假设|问题重述|参考文献", text), "论文含主要章节")
        # 分章节清单检查：写作阶段边写边勾，工作目录下应有自检表
        need(find_p4_checklist(root) is not None,
             "分章节清单检查：比赛工作目录存在自检表（论文/优秀论文自检表.md）")

    elif phase == "P5":
        text = _gather_text(root)
        need(not re.search(r"TODO|待补|占位|XXX|FIXME", text), "无 TODO/占位符残留")
        need(re.search(r"参考文献|References|\[\d+\]", text), "有参考文献/引用标注")
        anonymous_text = text
        for command in ("schoolname", "baominghao", "membera", "memberb", "memberc"):
            anonymous_text = re.sub(rf"\\{command}\s*\{{[^{{}}]*\}}", "", anonymous_text, flags=re.S)
        need(not re.search(r"大学|学院|导师|姓名", anonymous_text),
             "封皮后匿名化（官方封皮字段除外；启发式）")

    elif phase == "P6":
        sub = root / "提交附件"
        need(sub.is_dir() and any(sub.glob("*")), "提交附件目录非空")
        text = _gather_text(root)
        need(re.search(r"人工智能工具|AI工具|人工智能辅助|AI辅助", text), "有 AI 使用披露")
        need(any(root.rglob("*.pdf")), "有最终论文 PDF")
        # 自检表 100% 闭环（Wave6-B 硬退出）
        need(find_p6_checked(root) is not None,
             "P6 自检表闭环：《论文自检表_已勾选.md》已落盘")
        sidecar = find_sidecar(root)
        if sidecar is None:
            need(False, "人工条目裁决：待运行 paper_checklist（sidecar paper_checklist_decisions.json 缺失）")
        else:
            n = count_undecided_decisions(sidecar)
            if n < 0:
                need(False, "人工条目裁决：sidecar 已找到但无法解析未裁决项（请确认 paper_checklist --mark 已跑完）")
            else:
                need(n == 0, f"人工条目全部裁决：sidecar 无未裁决项（剩余 {n} 条）")

    passed = all(ok for ok, _ in items)
    return passed, items


def main(argv=None):
    ap = argparse.ArgumentParser(description="P0-P6 内容级门禁检查")
    ap.add_argument("--root", default=".", help="比赛工作目录（默认当前目录）")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--gate", choices=PHASES, help="只检查单个阶段")
    g.add_argument("--all", action="store_true", help="检查全部阶段")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"[FAIL] 目录不存在: {root}")
        return 1

    phases = [args.gate] if args.gate else PHASES
    results = {}
    overall = True
    for ph in phases:
        ok, items = check_phase(ph, root)
        results[ph] = {"passed": ok, "items": [{"ok": o, "desc": d} for o, d in items]}
        overall = overall and ok

    if args.json:
        print(__import__("json").dumps({"root": str(root), "overall": overall,
                                        "phases": results}, ensure_ascii=False, indent=2))
    else:
        for ph in phases:
            r = results[ph]
            print(f"[{ 'PASS' if r['passed'] else 'FAIL' }] {ph}")
            for it in r["items"]:
                print(f"    [{'x' if it['ok'] else ' '}] {it['desc']}")
        print(f"\n总体: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
