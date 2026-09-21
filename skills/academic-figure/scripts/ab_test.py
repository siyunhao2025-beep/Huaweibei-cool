#!/usr/bin/env python3
"""Manual paired-artifact rubric for academic-figure A/B evaluation.

Defines 5 test scenarios with objective scoring criteria.
Each scenario returns: asset_hit, font_ok, palette_ok, spine_ok, render_ok, vector_export.

This file does not generate figures or invent scores. With no arguments it
prints the five rubrics. ``--compare`` reads two complete, independently
recorded result files and reports only the observed rubric-score difference.
"""

from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

# ═══════════════════════════════════════════════════════════
# Test scenarios
# ═══════════════════════════════════════════════════════════

SCENARIOS = [
    {
        "id": "S1_pca",
        "name": "PCA from real data",
        "prompt": "对 simulated_data.csv 做 PCA 分析并可视化",
        "user_type": "knows_what_they_want",
        "expected": {
            "figure_type": "PCA",
            "asset_exists": True,
            "asset_path": "assets/figures/PCA/plot_PCA.R",
            "backend": "R",
            "checks": [
                "R script executed natively (not Python re-write)",
                "PNG rendered with png(type='cairo') NO showtext",
                "Font: Arial, base_size >= 8",
                "CNS palette used (blue/red/green, not ggplot2 defaults)",
                "cairo_pdf for vector output",
                "300dpi PNG",
            ],
        },
    },
    {
        "id": "S2_radar_violin_bar_pca",
        "name": "Four-panel mixed-backend composition",
        "prompt": "画雷达图、小提琴图、分组柱状图、PCA图，组合成一张",
        "user_type": "knows_figure_types",
        "expected": {
            "figure_type": "multi-panel",
            "asset_exists": True,
            "asset_paths": ["Radar/plot_comparison_radar.py", "GroupedViolin/plot_GroupedViolin.py",
                           "GroupedBarChart/plot_GroupedBarChartv1.py", "PCA/plot_PCA.R"],
            "all_assets_hit": True,
            "checks": [
                "Asset Confirmation Table present as first comment block",
                "Radar panel uses native run (not hand-written)",
                "PCA panel uses R native run (not Python re-write)",
                "4 panel labels consistent (a,b,c,d — same font, position)",
                "Layout ≥ 2x2, panel width ≥ 45mm",
                "Mixed R+Python handled via compose_figure (Python) loading R PNGs",
            ],
        },
    },
    {
        "id": "S3_heatmap_nature_genetics",
        "name": "Nature Genetics-style heatmap",
        "prompt": "画一个 Nature Genetics 风格的差异基因表达热图",
        "user_type": "knows_journal",
        "expected": {
            "figure_type": "heatmap",
            "asset_exists": True,
            "asset_path": "assets/figures/3DHeatmap/ or CorrelationMatrix/",
            "journal": "Nature Genetics",
            "checks": [
                "journal_palette('nature') called",
                "Diverging RDBU colormap (not jet/rainbow)",
                "Row dendrogram ≤ 8mm",
                "Column annotation via ComplexHeatmap anno_points",
                "Vector PDF + cairo_pdf",
                "Arial font throughout",
            ],
        },
    },
    {
        "id": "S4_unknown_chart_type",
        "name": "Unsupported long-tail chart",
        "prompt": "画一个弦图展示六个群组之间的流动物流量",
        "user_type": "wants_uncommon_chart",
        "expected": {
            "figure_type": "chord diagram",
            "asset_exists": False,
            "checks": [
                "Skill does NOT error out or refuse",
                "Cross-type inheritance used (borrows from Sankey or network)",
                "CNS baseline colors and fonts applied",
                "User informed: 'no production script, using cross-type inheritance'",
                "Output is usable (not beautiful, but not broken)",
            ],
        },
    },
    {
        "id": "S5_analyze_vague",
        "name": "Vague data-visualization request",
        "prompt": "分析 simulated_data.csv 并可视化",
        "user_type": "vague_request",
        "expected": {
            "figure_type": "unknown",
            "checks": [
                "Step -1 fires FIRST: 'What are you trying to learn from this data?'",
                "Does NOT auto-generate 4-panel template",
                "After user answers, recommendation is question-directed (not generic)",
                "Panel count determined by distinct questions, not template",
            ],
        },
    },
]


# ═══════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════

def print_scenarios():
    """Print all 5 test scenarios with scoring rubrics."""
    print("=" * 60)
    print("Academic Figure Skill A/B Test Framework — 5 Scenarios")
    print("=" * 60)
    print()
    for s in SCENARIOS:
        total = len(s["expected"]["checks"])
        print(f"Scenario {s['id']}: {s['name']}")
        print(f"  Prompt: \"{s['prompt']}\"")
        print(f"  Type: {s['user_type']}")
        print(f"  Asset exists: {s['expected'].get('asset_exists', 'N/A')}")
        print(f"  Checks ({total}):")
        for i, c in enumerate(s["expected"]["checks"], 1):
            print(f"    {i}. {c}")
        print()


def score_scenario(scenario_id: str, checks_passed: list[bool], details: list[str] = None) -> dict:
    """Score a single scenario. Returns result dict."""
    scenario = next((s for s in SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        return {"error": f"Unknown scenario: {scenario_id}"}

    total = len(scenario["expected"]["checks"])
    if len(checks_passed) != total:
        raise ValueError(
            f"{scenario_id} requires exactly {total} check results; got {len(checks_passed)}"
        )
    if not all(isinstance(value, bool) for value in checks_passed):
        raise TypeError("checks_passed must contain booleans only")
    passed = sum(1 for b in checks_passed if b)

    check_details = []
    for i, (ck, pk) in enumerate(zip(scenario["expected"]["checks"], checks_passed)):
        check_details.append({
            "index": i + 1,
            "description": ck,
            "passed": pk,
        })

    return {
        "scenario_id": scenario_id,
        "name": scenario["name"],
        "passed": passed,
        "total": total,
        "pass_rate": passed / total if total > 0 else 0,
        "checks": check_details,
        "details": details or [],
    }


def validate_result_set(payload: object, label: str) -> dict:
    """Reject missing or internally inconsistent manual measurements."""
    if not isinstance(payload, dict):
        raise ValueError(f"{label} result must be a JSON object")
    validated = {}
    for scenario in SCENARIOS:
        scenario_id = scenario["id"]
        row = payload.get(scenario_id)
        if not isinstance(row, dict):
            raise ValueError(f"{label} is missing scenario {scenario_id}")
        expected_total = len(scenario["expected"]["checks"])
        passed = row.get("passed")
        total = row.get("total")
        rate = row.get("pass_rate")
        if isinstance(passed, bool) or not isinstance(passed, int):
            raise ValueError(f"{label}/{scenario_id}.passed must be an integer")
        if total != expected_total or not 0 <= passed <= total:
            raise ValueError(
                f"{label}/{scenario_id} must satisfy 0 <= passed <= total == {expected_total}"
            )
        expected_rate = passed / total
        if isinstance(rate, bool) or not isinstance(rate, (int, float)):
            raise ValueError(f"{label}/{scenario_id}.pass_rate must be numeric")
        if not math.isclose(float(rate), expected_rate, rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"{label}/{scenario_id}.pass_rate is inconsistent with passed/total")
        validated[scenario_id] = row
    return validated


def load_result_set(path: Path, label: str) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"{label} result file does not exist: {path}")
    with path.open("r", encoding="utf-8-sig") as handle:
        return validate_result_set(json.load(handle), label)


def print_ab_report(baseline: dict, acad_fig_skill: dict):
    """Print A/B comparison report."""
    print("=" * 60)
    print("Academic Figure Skill A/B Comparison — Baseline vs Academic Figure Skill")
    print("=" * 60)
    print()

    baseline_total = acad_fig_skill_total = 0
    baseline_pass = acad_fig_skill_pass = 0

    for s in SCENARIOS:
        sid = s["id"]
        bl = baseline.get(sid, {})
        cn = acad_fig_skill.get(sid, {})

        bl_rate = bl["pass_rate"]
        cn_rate = cn["pass_rate"]
        delta = cn_rate - bl_rate

        if delta > 0:
            arrow = "+"
        elif delta < 0:
            arrow = ""
        else:
            arrow = "="

        print(f"  {sid}: Baseline={bl_rate:.0%}  Academic Figure Skill={cn_rate:.0%}  ({arrow}{delta:+.0%})")

        baseline_total += bl["total"]
        acad_fig_skill_total += cn["total"]
        baseline_pass += bl["passed"]
        acad_fig_skill_pass += cn["passed"]

    bl_overall = baseline_pass / baseline_total if baseline_total > 0 else 0
    cn_overall = acad_fig_skill_pass / acad_fig_skill_total if acad_fig_skill_total > 0 else 0

    print()
    print(f"  OVERALL: Baseline={bl_overall:.0%}  Academic Figure Skill={cn_overall:.0%}  (Δ={cn_overall - bl_overall:+.0%})")
    print("=" * 60)

    if cn_overall > bl_overall:
        print("Observed result: the skill artifact has the higher rubric score.")
    elif cn_overall == bl_overall:
        print("Observed result: the paired artifacts have equal rubric scores.")
    else:
        print("Observed result: the skill artifact has the lower rubric score; investigate before use.")
    print("This comparison does not by itself establish causal or general quality improvement.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare", action="store_true", help="compare two complete measured result files")
    parser.add_argument(
        "--baseline-file", type=Path,
        default=SKILL_DIR / "scripts" / ".ab_baseline.json",
    )
    parser.add_argument(
        "--skill-file", type=Path,
        default=SKILL_DIR / "scripts" / ".ab_academic-figure-skill.json",
    )
    args = parser.parse_args(argv)
    if not args.compare:
        print_scenarios()
        print("Generate paired artifacts from identical inputs, then score both with the checks above.")
        print()
        print(f"Expected result files: {SKILL_DIR / 'scripts' / '.ab_baseline.json'} and .ab_academic-figure-skill.json")
        return 0
    try:
        baseline = load_result_set(args.baseline_file, "baseline")
        academic = load_result_set(args.skill_file, "skill")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"A/B comparison refused: {exc}", file=sys.stderr)
        return 2
    print_ab_report(baseline, academic)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
