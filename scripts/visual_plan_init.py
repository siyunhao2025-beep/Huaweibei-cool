#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_求解规范/tools/，相对路径已改 CLI 参数驱动。
"""Create a draft Huawei Cup visual-evidence plan for a new problem set."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_EVIDENCE = (
    ("mechanism_geometry", "模型机理、几何或数据流是否需要可视解释？"),
    ("main_result", "本问最重要的定量结论是什么？"),
    ("independent_validation", "什么独立证据能够验证主结果？"),
    ("sensitivity_robustness", "哪些输入、参数或扰动会改变结论？"),
)


def make_problem(problem_id: str, complexity: str) -> dict:
    prefix = problem_id.replace(" ", "-")
    evidence = []
    for index, (category, question) in enumerate(REQUIRED_EVIDENCE, start=1):
        evidence.append({
            "evidence_id": f"{prefix}-E{index:02d}",
            "category": category,
            "question": question,
            "applicability": "pending",
            "reason": "",
            "data_shape": "pending",
            "representation": "pending",
            "result_files": [],
            "figure_ids": [],
        })
    return {
        "problem_id": problem_id,
        "complexity": complexity,
        "claims": [{"claim_id": f"{prefix}-C01", "text": "待填写：可复算的核心结论"}],
        "evidence_matrix": evidence,
        "figures": [],
        "schematics": [],
        "low_figure_exception": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-title", required=True)
    parser.add_argument("--problem-id", action="append", required=True,
                        help="Repeat once per problem, for example --problem-id 问题一")
    parser.add_argument("--complexity", choices=("simple", "standard", "complex"), default="standard")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing draft")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing plan: {output}")
    plan = {
        "schema_version": "1.0",
        "project_title": args.project_title,
        "plan_status": "draft",
        "visual_encoding_path": "求解/视觉编码表.md",
        "problems": [make_problem(pid, args.complexity) for pid in args.problem_id],
        "global_figures": [],
        "flowcharts": [{
            "scope": "全篇",
            "needed": "pending",
            "reason": "",
            "plan_id": None,
            "status": "pending",
        }],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "DRAFT_CREATED", "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
