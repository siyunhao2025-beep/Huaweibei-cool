#!/usr/bin/env python3
# [来源] 移植自 v2.1 华为杯_论文规范模板/tools/，相对路径已改为 CLI 参数驱动，Wave3 验证编译链路。
"""Calibrate role-based chapter page windows from exemplar PDFs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def inclusive(start, end):
    return max(0, end - start + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    by_role = {}
    observations = []
    for sample in baseline.get("samples", []):
        for section in sample.get("sections", []):
            if section.get("role") not in {"problem", "preliminary", "evaluation", "conclusion"}:
                continue
            pages = inclusive(section["start"], section["end"])
            role = section["role"]
            by_role.setdefault(role, []).append(pages)
            observations.append({"sample": sample["id"], "name": section["name"], "role": role, "pages": pages})
    targets = {}
    for role, values in sorted(by_role.items()):
        values.sort()
        lo = min(values)
        hi = max(values)
        # A role window is intentionally broad: it detects an outlier rather
        # than forcing every problem to imitate one exemplar.
        if role == "problem":
            min_pages = max(1, min(lo, 3))
            max_pages = max(hi, 14)
        elif role == "preliminary":
            min_pages, max_pages = 1, max(8, hi)
        else:
            min_pages, max_pages = 1, max(6, hi)
        targets[role] = {"min_pages": min_pages, "max_pages": max_pages, "observed": values}
    result = {
        "version": 1,
        "required_body_pages": 0,
        "page_system": baseline.get("page_number_system", "printed"),
        "body_definition": baseline.get("body_definition"),
        "role_windows_enabled": False,
        "role_targets": targets,
        "observations": observations,
        "body_page_gate_mode": "off",
        "body_page_gate_authority": "official_2026_no_limit_stated",
        "policy": "Historical role windows are descriptive only. Keep the page gate off unless the current problem statement or a later official notice explicitly defines a limit.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
