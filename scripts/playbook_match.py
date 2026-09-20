#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""playbook_match.py — 题面 → 8 原型/playbook 规则匹配。

加载 playbooks/match_rules.json，对题面文本做关键词命中，输出：
  - 匹配到的原型（top1，按 confidence 与 tie-break）
  - 命中的规则、置信度、依据关键词
  - 推荐的 playbook 方法卡列表（glob playbooks/<原型>/*.md）

这是粗筛工具：一篇论文常跨多原型，top1 仅供建议，不替代人工读题。

用法：
  python scripts/playbook_match.py --txt problem_text.txt
  python scripts/playbook_match.py --stdin < problem_text.txt
  echo "预测销量并做调度优化" | python scripts/playbook_match.py --stdin
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES = REPO_ROOT / "playbooks" / "match_rules.json"


def load_rules(path: Path) -> dict:
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def recommend_cards(archetype: str) -> list:
    """列出某原型目录下的方法卡（排除 00_overview.md）。"""
    d = REPO_ROOT / "playbooks" / archetype
    if not d.is_dir():
        return []
    cards = []
    for p in sorted(d.glob("*.md")):
        if p.name == "00_overview.md":
            continue
        cards.append(f"playbooks/{archetype}/{p.name}")
    return cards


def match(text: str, rules: dict) -> list:
    """返回每条命中规则的得分记录，按 confidence 降序。"""
    hits = []
    text_lower = text.lower()
    for r in rules.get("rules", []):
        matched = [kw for kw in r["keywords"] if kw.lower() in text_lower]
        if not matched:
            continue
        # 命中词越多，置信度略加权，但不超过规则 confidence 太多
        score = r["confidence"]
        if len(matched) >= 2:
            score = min(0.99, score + 0.05 * (len(matched) - 1))
        hits.append({
            "rule_id": r["rule_id"],
            "archetype": r["archetype"],
            "confidence": round(score, 3),
            "base_confidence": r["confidence"],
            "matched_keywords": matched,
            "evidence_papers": r.get("evidence_papers"),
            "note": r.get("note", ""),
        })
    hits.sort(key=lambda h: (-h["confidence"], h["rule_id"]))
    return hits


def pick_top(hits: list, rules: dict) -> dict:
    """按 tie_break 选 top1。无命中返回 unknown。"""
    if not hits or hits[0]["confidence"] < 0.5:
        return {"archetype": "unknown", "confidence": 0.0,
                "reason": "无关键词命中或置信度<0.5，需人工读题判断"}
    # 同原型合并：同一原型多条规则命中，取最高
    best = {}
    for h in hits:
        a = h["archetype"]
        if a not in best or h["confidence"] > best[a]["confidence"]:
            best[a] = h
    ordered = sorted(best.values(), key=lambda h: (-h["confidence"], h["rule_id"]))
    top = ordered[0]
    return {
        "archetype": top["archetype"],
        "confidence": top["confidence"],
        "runner_up": ordered[1]["archetype"] if len(ordered) > 1 else None,
        "note": rules.get("limitation", ""),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="题面→8原型/playbook 规则匹配")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--txt", help="题面文本文件路径")
    g.add_argument("--stdin", action="store_true", help="从标准stdin读题面")
    ap.add_argument("--rules", default=str(DEFAULT_RULES), help="match_rules.json 路径")
    ap.add_argument("--json", action="store_true", help="以JSON输出")
    args = ap.parse_args(argv)

    if args.txt:
        text = Path(args.txt).read_text(encoding="utf-8-sig", errors="ignore")
    else:
        text = sys.stdin.read()

    rules = load_rules(Path(args.rules))
    hits = match(text, rules)
    top = pick_top(hits, rules)
    cards = recommend_cards(top["archetype"])

    if args.json:
        out = {"top": top, "all_hits": hits, "recommended_cards": cards}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print("=== 题面原型匹配（粗筛，仅供建议）===")
    print(f"主原型: {top['archetype']}  (置信度 {top['confidence']})")
    if top.get("runner_up"):
        print(f"辅/次选: {top['runner_up']}")
    if top["archetype"] == "unknown":
        print("→ " + top["reason"])
    print("\n命中规则:")
    if not hits:
        print("  (无关键词命中)")
    for h in hits:
        print(f"  [{h['rule_id']}] {h['archetype']:18s} conf={h['confidence']} "
              f"命中={h['matched_keywords']}  依据:{h['note']}")
    print("\n推荐方法卡:")
    for c in cards:
        print("  - " + c)
    print("\n提示: 关键词粗筛，一篇常跨多原型；请结合题意人工确认主/辅原型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
