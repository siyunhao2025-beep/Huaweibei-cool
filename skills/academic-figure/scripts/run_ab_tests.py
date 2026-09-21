#!/usr/bin/env python3
"""Evidence-bound static capability audit for the academic-figure skill.

This script checks that the assets and rules required by the five historical
A/B scenarios are present.  It deliberately does *not* invent a bare-model
score or claim a quality improvement.  A real A/B conclusion requires paired
rendered artifacts scored with ``ab_test.py`` under the same inputs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent


def _scenario(checks: list[tuple[str, bool]]) -> dict:
    items = [{"check": name, "passed": bool(passed)} for name, passed in checks]
    passed = sum(item["passed"] for item in items)
    return {
        "passed": passed,
        "total": len(items),
        "all_passed": passed == len(items),
        "checks": items,
    }


def run_all() -> dict:
    scripts = SKILL_DIR / "scripts"
    references = SKILL_DIR / "references"
    figures = SKILL_DIR / "assets" / "figures"

    compose = (scripts / "compose.py").read_text(encoding="utf-8")
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    colors = (references / "color-palettes.md").read_text(encoding="utf-8")
    typography = (references / "typography.md").read_text(encoding="utf-8")
    exports = (references / "export-specs.md").read_text(encoding="utf-8")
    checklist = (references / "checklist.md").read_text(encoding="utf-8")

    scenarios = {
        "S1_pca": _scenario([
            ("PCA R asset exists", (figures / "PCA" / "plot_PCA.R").is_file()),
            ("R PNG uses Cairo", 'type="cairo"' in compose or "type='cairo'" in compose),
            ("semantic palette documented", "#2166AC" in colors and "#B2182B" in colors),
            ("Arial fallback documented", "Arial" in typography),
            ("vector Cairo export documented", "cairo_pdf" in exports),
            ("300 dpi rule documented", "300" in exports),
        ]),
        "S2_multipanel": _scenario([
            ("Radar asset exists", (figures / "Radar" / "plot_comparison_radar.py").is_file()),
            ("GroupedViolin asset exists", (figures / "GroupedViolin" / "plot_GroupedViolin.py").is_file()),
            ("GroupedBarChart asset exists", (figures / "GroupedBarChart" / "plot_GroupedBarChartv1.py").is_file()),
            ("PCA asset exists", (figures / "PCA" / "plot_PCA.R").is_file()),
            ("asset confirmation rule exists", "Asset Confirmation Table" in skill),
            ("composition engine exists", "def compose_figure" in compose),
        ]),
        "S3_journal_heatmap": _scenario([
            ("journal palette selector exists", "def journal_palette" in compose),
            ("Nature palette exists", '"nature"' in compose.lower()),
            ("Cell palette exists", '"cell"' in compose.lower()),
            ("Science palette exists", '"science"' in compose.lower()),
            ("jet/rainbow QA guard exists", "AP-2" in checklist and "rainbow" in checklist.lower()),
        ]),
        "S4_unknown_chart": _scenario([
            ("cross-type inheritance documented", "cross-type" in skill.lower()),
            ("asset borrowing documented", "borrow" in skill.lower()),
            ("long-tail routing documented", "long-tail" in skill.lower()),
        ]),
        "S5_vague_request": _scenario([
            ("Step -1 exists", "Step -1" in skill),
            (
                "anti-template rule exists",
                "not from a template" in skill.lower()
                and "never generate generic" in skill.lower(),
            ),
            ("task understanding precedes drawing", "Understand the Task" in skill),
        ]),
    }
    total = sum(item["total"] for item in scenarios.values())
    passed = sum(item["passed"] for item in scenarios.values())
    return {
        "audit_type": "static_capability_only",
        "empirical_quality_claim": False,
        "summary": {"passed": passed, "total": total, "all_passed": passed == total},
        "scenarios": scenarios,
        "next_step_for_real_ab": (
            "Generate paired baseline/skill artifacts from identical inputs, record artifact hashes and "
            "raw measurements, then score them with ab_test.py."
        ),
    }


def main() -> int:
    report = run_all()
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print("Academic Figure Skill static capability audit")
        for scenario_id, result in report["scenarios"].items():
            state = "PASS" if result["all_passed"] else "FAIL"
            print(f"[{state}] {scenario_id}: {result['passed']}/{result['total']}")
            for item in result["checks"]:
                print(f"  {'PASS' if item['passed'] else 'FAIL'}  {item['check']}")
        print(f"Summary: {summary['passed']}/{summary['total']}")
        print("No empirical A/B improvement is claimed by this static audit.")
    return 0 if report["summary"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
