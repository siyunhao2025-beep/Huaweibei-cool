#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_roadmap.py — 技术路线图（论文图1）规格校验器。

校验项：
  schema_valid            符合 assets/roadmap/roadmap.schema.json
  subquestion_covered     subquestion_mapping 中每个小问至少映射一个真实存在的节点
  no_isolated_nodes       除 input/output 层外，每个节点至少一条入边或出边
  cbf_safe_colors         节点 color（若显式给出）必须在色盲友好色板内
  has_feedback_loop       至少一条 dashed 反馈回路（WARN 级，缺则提醒）
  node_method_nonempty    节点 method 非空（与 schema 双保险）

用法：
    python scripts/audit_roadmap.py --spec roadmap.yaml
    python scripts/audit_roadmap.py --spec roadmap.yaml --report report.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "assets" / "roadmap" / "roadmap.schema.json"

# 与 render_roadmap.py 同源的色盲友好色板
LAYER_COLORS = {
    "input": "#2166AC", "preprocess": "#4393C3", "model": "#1B7837",
    "solve": "#F1A340", "validate": "#762A83", "output": "#B2182B",
}
CBF_SAFE_COLORS = set(LAYER_COLORS.values()) | {
    "#D6604D", "#5AAE61", "#B35806", "#9970AB", "#999999", "#666666", "#222222",
}
ENDPOINT_LAYERS = {"input", "output"}


def load_spec(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def audit(spec: dict, schema_path: Path = SCHEMA_PATH) -> dict:
    checks: list[dict] = []
    failures: list[dict] = []
    warnings: list[dict] = []

    def add(code: str, ok: bool, severity: str = "FAIL", **details) -> None:
        item = {"code": code, "ok": ok, "severity": "PASS" if ok else severity, **details}
        checks.append(item)
        if not ok:
            (failures if severity == "FAIL" else warnings).append(item)

    # 1) schema
    try:
        import jsonschema
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(spec, schema)
        add("schema_valid", True)
    except FileNotFoundError:
        add("schema_valid", False, error=f"schema 未找到: {schema_path}")
        return _result(checks, failures, warnings)
    except Exception as exc:
        add("schema_valid", False, error=str(exc))
        return _result(checks, failures, warnings)

    nodes = spec.get("nodes", [])
    node_ids = [n.get("id") for n in nodes]
    node_set = set(node_ids)
    edges = spec.get("edges", [])
    mapping = spec.get("subquestion_mapping", {})

    # 2) 小问覆盖
    missing_nodes: dict[str, list[str]] = {}
    uncovered: list[str] = []
    for subq, nids in mapping.items():
        real = [n for n in nids if n in node_set]
        ghost = [n for n in nids if n not in node_set]
        if ghost:
            missing_nodes[subq] = ghost
        if not real:
            uncovered.append(subq)
    add("subquestion_uncovered", not uncovered,
        uncovered=uncovered, message="未被任何节点覆盖的小问")
    add("subquestion_node_exists", not missing_nodes,
        ghost=missing_nodes, message="映射到不存在节点 id 的小问")

    # 3) 孤立节点（input/output 层除外）
    has_edge: set[str] = set()
    for e in edges:
        has_edge.add(e.get("from"))
        has_edge.add(e.get("to"))
    isolated = [n["id"] for n in nodes
                if n.get("layer") not in ENDPOINT_LAYERS and n["id"] not in has_edge]
    add("no_isolated_nodes", not isolated, isolated=isolated,
        message="既无入边也无出边的中间层节点")

    # 4) 色盲友好配色
    bad_colors = [{"id": n["id"], "color": n["color"]}
                  for n in nodes
                  if n.get("color") and str(n["color"]).upper() not in CBF_SAFE_COLORS]
    add("cbf_safe_colors", not bad_colors, bad=bad_colors,
        message="显式指定的节点色不在色盲友好色板内（勿用 jet/rainbow/tab10/Set1）")

    # 5) 反馈回路（WARN）
    has_dashed = any(e.get("type") == "dashed" for e in edges)
    add("has_feedback_loop", has_dashed, severity="WARN",
        message="缺虚线反馈回路（迭代/调参/换模型），路线图会被质疑无迭代优化")

    # 6) method 非空（schema 已 minLength，双保险）
    empty_method = [n["id"] for n in nodes if not str(n.get("method", "")).strip()]
    add("node_method_nonempty", not empty_method, empty=empty_method,
        message="节点缺方法名（框里只有‘模型1’不行）")

    return _result(checks, failures, warnings)


def _result(checks, failures, warnings) -> dict:
    return {
        "status": "FAIL" if failures else "PASS",
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "summary": {"checks": len(checks), "failures": len(failures), "warnings": len(warnings)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", type=Path, required=True, help="YAML 路线图规格")
    parser.add_argument("--report", type=Path, default=None, help="可选：JSON 报告写出路径")
    args = parser.parse_args()
    spec = load_spec(args.spec)
    result = audit(spec)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
