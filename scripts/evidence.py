#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evidence.py — 证据账本校验。

输入用户维护的证据账本 JSON，检查每条证据是否合规：
  - 必需字段是否齐全（结论/来源类型/来源定位/置信度/验证状态）
  - 置信度是否在 {A,B,C} 内
  - 来源类型=AI生成 时，来源定位是否填了 AI 工具名+版本（可解析）
  - C 级/风险项是否被标记
输出缺失/不规范项清单，退出码 0=全部通过，1=有问题。

账本 schema（每条一个对象）:
  {"claim": "...", "source_type": "code|data|literature|official|ai|assumption",
   "source_loc": "...", "confidence": "A|B|C", "verify_status": "verified|pending|risk"}

用法:
  python scripts/evidence.py --ledger evidence.json
  python scripts/evidence.py --ledger evidence.json --json
"""
import argparse
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = ["claim", "source_type", "source_loc", "confidence", "verify_status"]
VALID_CONF = {"A", "B", "C"}
VALID_VERIFY = {"verified", "pending", "risk"}
AI_SOURCE_TYPES = {"ai"}


def check_entry(idx: int, e: dict) -> list:
    issues = []
    # 必需字段
    for f in REQUIRED_FIELDS:
        if f not in e or e[f] in (None, "", []):
            issues.append(f"第{idx}条 缺字段: {f}")
    # 置信度合法
    conf = e.get("confidence")
    if conf and conf not in VALID_CONF:
        issues.append(f"第{idx}条 置信度非法: {conf}（应 A/B/C）")
    # 验证状态合法
    vs = e.get("verify_status")
    if vs and vs not in VALID_VERIFY:
        issues.append(f"第{idx}条 验证状态非法: {vs}（应 verified/pending/risk）")
    # AI 生成必须有来源定位（工具名+版本）
    if e.get("source_type") in AI_SOURCE_TYPES:
        loc = str(e.get("source_loc", ""))
        if len(loc.strip()) < 3:
            issues.append(f"第{idx}条 是AI生成但来源定位为空（须写AI工具名+版本+机构）")
        # AI 生成默认应为 risk/pending
        if e.get("verify_status") == "verified":
            issues.append(f"第{idx}条 AI生成却标 verified（AI未核实应标 risk/pending）")
    # C 级假设不能标 verified
    if conf == "C" and e.get("verify_status") == "verified":
        issues.append(f"第{idx}条 C级(假设/推断)却标 verified，应改 pending/risk")
    # 来源定位可解析启发式：不能是纯占位
    loc = str(e.get("source_loc", "")).strip()
    if loc and loc.lower() in {"todo", "待补", "tbd", "xxx", "..."}:
        issues.append(f"第{idx}条 来源定位是占位符: {loc}")
    return issues


def main(argv=None):
    ap = argparse.ArgumentParser(description="证据账本合规校验")
    ap.add_argument("--ledger", required=True, help="证据账本 JSON 路径")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args(argv)

    p = Path(args.ledger)
    if not p.exists():
        print(f"[FAIL] 账本不存在: {p}")
        return 1
    try:
        data = json.load(open(p, encoding="utf-8-sig"))
    except Exception as ex:
        print(f"[FAIL] JSON 解析失败: {ex}")
        return 1

    entries = data if isinstance(data, list) else data.get("entries", [])
    all_issues = []
    for i, e in enumerate(entries, 1):
        if not isinstance(e, dict):
            all_issues.append(f"第{i}条 不是对象: {type(e).__name__}")
            continue
        all_issues.extend(check_entry(i, e))

    if args.json:
        print(json.dumps({"total": len(entries), "issues": all_issues,
                          "ok": len(all_issues) == 0}, ensure_ascii=False, indent=2))
    else:
        print(f"证据条目 {len(entries)} 条，问题 {len(all_issues)} 项")
        for it in all_issues:
            print("  - " + it)
        if not all_issues:
            print("全部合规。")
    return 0 if not all_issues else 1


if __name__ == "__main__":
    sys.exit(main())
