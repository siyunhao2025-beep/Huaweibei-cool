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
            "table_ids": [],
        })
    return {
        "problem_id": problem_id,
        "complexity": complexity,
        "claims": [{"claim_id": f"{prefix}-C01", "text": "待填写：可复算的核心结论"}],
        "evidence_matrix": evidence,
        "figures": [],
        "tables": [],
        "schematics": [],
        "low_figure_exception": None,
        "low_table_exception": None,
    }


def make_complex_f01(problem_id: str) -> dict:
    """Return a schema-valid draft entry for the paper-level complex F01 route."""
    prefix = problem_id.replace(" ", "-")
    binding = "求解/framework/F01_framework_binding.json"
    report = "求解/framework/F01_framework_audit.json"
    return {
        "figure_id": "F01",
        "scope": "全篇",
        "scientific_question": "各问的数据、模型、验证与独立测试如何形成完整证据链？",
        "claim_ids": [f"{prefix}-C01"],
        "evidence_ids": [f"{prefix}-E01"],
        "archetype": "schematic_led",
        "layout": "paper-level multi-question framework",
        "hero_panel": "a",
        "panels": [{
            "panel_id": "a",
            "question": "全篇输入、各问机制、验证控制和独立测试边界如何衔接？",
            "figure_type": "framework",
            "figure_family": "flow_structure",
            "result_file": binding,
            "fields": ["输入", "各问机制", "验证", "独立测试", "证据输出"],
            "units": ["", "", "", "", ""],
            "visual_encoding": "中文优先；实线为数据/评价流，虚线仅表示真实验证控制",
            "asset_directory": "Framework",
            "asset_mode": "visual_adapt",
        }],
        "script": binding,
        "outputs": {
            "vector": "论文/figures/F01.pdf",
            "preview": "论文/figures/F01.png",
        },
        "statistics_report": report,
        "qa_report": report,
        "paper": {
            "chapter": "总体问题分析",
            "label": "fig:F01",
            "caption": "论文总体技术路线与证据流",
            "reference_context": "正文先说明跨问依赖、验证控制和独立测试边界，再引用本图。",
        },
        "status": "planned",
        "role": "complex_multi_question_framework",
        "route": "paper-framework-figure-studio-pro S0--S5",
        "complex_framework": True,
        "framework_binding": binding,
        "framework_audit_report": report,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-title", required=True)
    parser.add_argument("--problem-id", action="append", required=True,
                        help="Repeat once per problem, for example --problem-id 问题一")
    parser.add_argument("--complexity", choices=("simple", "standard", "complex"), default="standard")
    parser.add_argument(
        "--complex-f01",
        action="store_true",
        help="登记一张走 paper-framework-figure-studio-pro 的复杂多问 F01 草案",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing draft")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"Refusing to overwrite existing plan: {output}")
    plan = {
        "schema_version": "1.2",
        "project_title": args.project_title,
        "plan_status": "draft",
        "figure_count_lock": {
            "status": "proposed",
            "proposed_total": 1 if args.complex_f01 else 0,
            "user_requested_total": None,
            "final_total": 1 if args.complex_f01 else 0,
            "counting_rule": "numbered_top_level_figures",
            "confirmation_record": "",
        },
        "visual_encoding_path": "求解/视觉编码表.md",
        "color_semantics": {
            "baseline": "#2166AC",
            "risk_highlight": "#B2182B",
            "improvement": "#1B7837",
            "secondary": "#F1A340",
            "additional_model": "#762A83",
            "background": "#999999",
        },
        "problems": [make_problem(pid, args.complexity) for pid in args.problem_id],
        "global_figures": [make_complex_f01(args.problem_id[0])] if args.complex_f01 else [],
        "global_tables": [],
        "flowcharts": [{
            "scope": "全篇",
            "needed": "yes" if args.complex_f01 else "pending",
            "reason": (
                "复杂多问论文需要呈现跨问数据、验证控制与独立测试边界。"
                if args.complex_f01 else ""
            ),
            "plan_id": "F01" if args.complex_f01 else None,
            "status": "planned" if args.complex_f01 else "pending",
        }],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "DRAFT_CREATED", "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
