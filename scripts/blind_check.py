#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blind_check.py — 留出盲检：对未参与深卡的论文跑 playbook_match，对照其简卡 task_types。

从指定年份简卡中排除已入深卡的 paper_id，跨赛道取样 N 篇，用
"标题+task_types+models"作题面跑 playbook_match，比较匹配原型与 task_types
推断原型是否一致。如实输出命中与失败案例。

用法:
  python scripts/blind_check.py --year 2023 --n 10
"""
import argparse
import glob
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("pm", REPO / "scripts" / "playbook_match.py")
pm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pm)

# task_types/models/title -> 期望原型（粗启发，用于对照，非金标准）
EXPECT_RULES = [
    ("预测", "prediction"), ("预报", "prediction"), ("时序", "prediction"), ("趋势", "prediction"),
    ("评价", "evaluation"), ("评估", "evaluation"), ("打分", "evaluation"), ("排序", "evaluation"), ("指标体系", "evaluation"),
    ("优化", "optimization"), ("调度", "optimization"), ("分配", "optimization"), ("选址", "optimization"),
    ("排样", "optimization"), ("路径", "optimization"), ("规划", "optimization"), ("整数规划", "optimization"), ("成本", "optimization"),
    ("分类", "classification-cv"), ("识别", "classification-cv"), ("聚类", "classification-cv"),
    ("检测", "classification-cv"), ("分割", "classification-cv"),
    ("微分方程", "mechanism"), ("动力学", "mechanism"), ("机理", "mechanism"),
    ("Markov", "mechanism"), ("马尔可夫", "mechanism"), ("传染病", "mechanism"),
    ("信号", "signal"), ("频谱", "signal"), ("滤波", "signal"), ("雷达", "signal"), ("振动", "signal"),
    ("图", "spatial-graph"), ("网络", "spatial-graph"), ("空间", "spatial-graph"), ("GIS", "spatial-graph"), ("插值", "spatial-graph"),
    ("仿真", "simulation"), ("蒙特卡洛", "simulation"), ("排队", "simulation"), ("随机", "simulation"),
]


def expect_archetype(b):
    blob = " ".join(b.get("task_types", []) + b.get("models_and_algorithms", []) + [b["title"]])
    for kw, a in EXPECT_RULES:
        if kw in blob:
            return a
    return "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(description="留出盲检：playbook_match 对未深卡论文的对照")
    ap.add_argument("--year", default="2023")
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args(argv)

    rules = pm.load_rules(REPO / "playbooks" / "match_rules.json")
    brief = json.load(open(REPO / "corpus" / "cards" / "brief" / f"{args.year}.json",
                           encoding="utf-8-sig"))
    deep_ids = {os.path.splitext(os.path.basename(p))[0]
                for p in glob.glob(str(REPO / "corpus" / "cards" / "deep" / "*.json"))}
    sel = [b for b in brief if b["paper_id"] not in deep_ids]

    by = {}
    for b in sel:
        by.setdefault(b["track"], []).append(b)
    # 分层取样：跨赛道尽量均匀，每赛道取 ceil(n/len(tracks))
    per = max(1, (args.n + len(by) - 1) // max(1, len(by)))
    picks = []
    for t in sorted(by):
        picks += by[t][:per]
    picks = picks[:args.n]

    match_n = 0
    rows = []
    for b in picks:
        text = (b["title"] + " " + " ".join(b.get("task_types", [])) + " "
                + " ".join(b.get("models_and_algorithms", [])))
        hits = pm.match(text, rules)
        top = pm.pick_top(hits, rules)
        exp = expect_archetype(b)
        got = top["archetype"]
        ok = got == exp
        match_n += int(ok)
        rows.append((b["paper_id"], got, top["confidence"], exp, ok, b["title"]))

    print(f"{'paper_id':28s} {'match_top':16s} conf   expected(tt)         align")
    for pid, got, conf, exp, ok, title in rows:
        print(f"{pid:28s} {got:16s} {conf:<6.2f} {exp:22s} {'Y' if ok else 'N'}  {title[:24]}")
    print(f"\n对齐 {match_n}/{len(picks)} = {round(100*match_n/max(1,len(picks)))}%")
    print("注: expected 由 task_types 关键词粗推，非金标准；'N' 多为题面词不足或跨原型。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
