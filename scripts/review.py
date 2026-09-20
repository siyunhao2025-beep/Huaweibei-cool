#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""review.py — 评审团启发式模拟打分。

输入论文摘要+章节文本（文件或stdin），按官方四标准做关键词/结构检查：
  假设合理性 / 建模创造性 / 结果正确性 / 文字表述清晰度
输出各维度提示分(0-5)与改进建议。

【重要】这是启发式关键词检查，不是真评审，不能替代人工判断。

用法:
  python scripts/review.py --paper paper.txt
  python scripts/review.py --paper paper.txt --json
  cat paper.txt | python scripts/review.py --stdin
"""
import argparse
import re
import sys
from pathlib import Path

DIMENSIONS = {
    "假设合理性": {
        "good": [r"假设", r"合理性", r"影响", r"简化"],
        "bad": [r"不影响结果", r"无需假设", r"假设如下$"],
    },
    "建模创造性": {
        "good": [r"改进", r"针对", r"对比", r"组合", r"迁移", r"残差", r"消融"],
        "bad": [r"良好效果", r"广泛应用", r"具有重要意义", r"提供有力支撑"],
    },
    "结果正确性": {
        "good": [r"RMSE", r"误差", r"准确率", r"对比", r"验证", r"灵敏度", r"鲁棒", r"%"],
        "bad": [r"效果良好", r"精度较高", r"结果令人满意"],
    },
    "文字表述清晰度": {
        "good": [r"如图", r"如表", r"式\s*\d", r"其中", r"因此"],
        "bad": [r"综上所述", r"由此可见", r"总而言之", r"众所周知"],
    },
}


def score_dimension(text: str, spec: dict) -> tuple:
    """0-5 启发分。good 命中加分，bad 命中扣分。"""
    good_hits = sum(len(re.findall(p, text)) for p in spec["good"])
    bad_hits = sum(len(re.findall(p, text)) for p in spec["bad"])
    score = 2.0 + min(good_hits, 6) * 0.5 - min(bad_hits, 6) * 0.5
    score = max(0.0, min(5.0, score))
    return round(score, 1), good_hits, bad_hits


def suggestions(dim: str, score: float, bad_hits: int) -> list:
    s = []
    if dim == "假设合理性" and score < 3.5:
        s.append("假设是否写了'内容+合理性+影响'？是否≥3条？")
    if dim == "建模创造性" and score < 3.5:
        s.append("有没有'上一模型哪不好→针对性改进'的因果链？还是并列堆算法？")
    if dim == "结果正确性" and score < 3.5:
        s.append("有没有多基线对比+量化误差？只报训练集不算验证。")
    if dim == "文字表述清晰度" and score < 3.5:
        s.append("删掉空泛连接词，每个结论句补数字或文献。")
    if bad_hits > 0:
        s.append("检出 AI 味套话，按 deai-writing 改写。")
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description="评审团启发式模拟打分（非真评审）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--paper", help="论文文本文件路径")
    g.add_argument("--stdin", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    text = Path(args.paper).read_text(encoding="utf-8", errors="ignore") if args.paper else sys.stdin.read()

    report = {}
    total = 0.0
    for dim, spec in DIMENSIONS.items():
        sc, gh, bh = score_dimension(text, spec)
        report[dim] = {"score": sc, "good_hits": gh, "bad_hits": bh,
                       "suggestions": suggestions(dim, sc, bh)}
        total += sc
    avg = round(total / len(DIMENSIONS), 1)

    if args.json:
        print(__import__("json").dumps({"avg": avg, "dimensions": report,
                                        "note": "启发式检查，非真评审"},
                                       ensure_ascii=False, indent=2))
    else:
        print("=== 评审团启发式模拟（非真评审，仅供查漏）===")
        for dim, r in report.items():
            print(f"{dim:12s} {r['score']}/5  (good命中{r['good_hits']}, AI味{r['bad_hits']})")
            for s in r["suggestions"]:
                print(f"    → {s}")
        print(f"\n平均 {avg}/5。最低维度即最该补的短板。")
        print("注意: 关键词启发，不代表官方评分。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
