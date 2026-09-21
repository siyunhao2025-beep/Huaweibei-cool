# -*- coding: utf-8 -*-
"""Regression checks for the Figure + Table evidence plan."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

import visual_plan_audit
import visual_plan_init


ROOT = Path(__file__).resolve().parents[1]


def _figure(fid: str, evidence_ids: list[str], question: str, family: str) -> dict:
    return {
        "figure_id": fid,
        "scope": "问题一",
        "scientific_question": question,
        "claim_ids": ["P1-C01"],
        "evidence_ids": evidence_ids,
        "archetype": "quantitative_grid",
        "layout": "1x1",
        "hero_panel": None,
        "panels": [{
            "panel_id": "a",
            "question": question,
            "figure_type": "line",
            "figure_family": family,
            "result_file": f"求解/results/{fid}.csv",
            "fields": ["x", "y"],
            "units": ["s", "1"],
            "visual_encoding": "蓝色基线，橙色候选；线型冗余编码",
            "asset_directory": "LineTrend",
            "asset_mode": "visual_adapt",
        }],
        "script": f"求解/scripts/{fid}.py",
        "outputs": {"vector": f"论文/figures/{fid}.pdf", "preview": f"论文/figures/{fid}.png"},
        "statistics_report": f"求解/reports/{fid}.json",
        "qa_report": f"求解/reports/{fid}_qa.json",
        "paper": {
            "chapter": "问题一",
            "label": f"fig:{fid}",
            "caption": question,
            "reference_context": "正文先解释比较口径，再引用本图。",
        },
        "status": "planned",
    }


def test_schema_and_initializer_include_table_ledger():
    schema = json.loads((ROOT / "scripts" / "视觉计划.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["properties"]["schema_version"]["const"] == "1.1"
    assert "global_tables" in schema["required"]
    assert "color_semantics" in schema["required"]
    assert schema["$defs"]["table"]["properties"]["paper"]["$ref"].endswith("table_paper_link")

    problem = visual_plan_init.make_problem("问题一", "standard")
    assert problem["tables"] == []
    assert problem["low_table_exception"] is None
    assert all(item["table_ids"] == [] for item in problem["evidence_matrix"])


def test_plan_audit_counts_non_redundant_tables(tmp_path):
    evidence = [
        {
            "evidence_id": "P1-E01", "category": "mechanism_geometry",
            "question": "模型结构如何影响结果？", "applicability": "applicable",
            "reason": "需要解释模型结构", "data_shape": "analytic_relation",
            "representation": "figure", "result_files": [], "figure_ids": ["F1"], "table_ids": [],
        },
        {
            "evidence_id": "P1-E02", "category": "main_result",
            "question": "主结果是否达到目标？", "applicability": "applicable",
            "reason": "题目要求定量回答", "data_shape": "ordered_series",
            "representation": "figure", "result_files": [], "figure_ids": ["F2"], "table_ids": ["T1"],
        },
        {
            "evidence_id": "P1-E03", "category": "independent_validation",
            "question": "独立样本误差是多少？", "applicability": "applicable",
            "reason": "需要核验泛化误差", "data_shape": "single_value",
            "representation": "table", "result_files": [], "figure_ids": [], "table_ids": ["T1"],
        },
        {
            "evidence_id": "P1-E04", "category": "sensitivity_robustness",
            "question": "参数扰动后结论稳定吗？", "applicability": "applicable",
            "reason": "需要验证结论稳定性", "data_shape": "multi_point_scan",
            "representation": "figure", "result_files": [], "figure_ids": ["F2"], "table_ids": [],
        },
    ]
    plan = {
        "schema_version": "1.1",
        "project_title": "视觉计划测试",
        "plan_status": "ready",
        "visual_encoding_path": "求解/视觉编码表.md",
        "color_semantics": visual_plan_audit.EXPECTED_COLOR_SEMANTICS,
        "problems": [{
            "problem_id": "问题一",
            "complexity": "simple",
            "claims": [{"claim_id": "P1-C01", "text": "候选方案在同口径下误差更低"}],
            "evidence_matrix": evidence,
            "figures": [
                _figure("F1", ["P1-E01"], "模型结构如何传递输入？", "mechanism"),
                _figure("F2", ["P1-E02", "P1-E04"], "主结果及扰动趋势如何？", "trend_scan"),
            ],
            "tables": [{
                "table_id": "T1",
                "scope": "问题一",
                "question": "主结果与独立误差的精确数值是多少？",
                "claim_ids": ["P1-C01"],
                "evidence_ids": ["P1-E02", "P1-E03"],
                "table_family": "main_result",
                "result_files": ["求解/results/T1.csv"],
                "columns": ["方法", "主指标", "独立误差"],
                "paper": {
                    "chapter": "问题一",
                    "label": "tab:T1",
                    "caption": "同口径结果与独立误差对比",
                    "reference_context": "正文引用精确值，不复述全部单元格。",
                },
                "status": "planned",
            }],
            "schematics": [],
            "low_figure_exception": None,
            "low_table_exception": None,
        }],
        "global_figures": [],
        "global_tables": [],
        "flowcharts": [{
            "scope": "全篇", "needed": "no",
            "reason": "现有技术路线图已覆盖流程，不需要额外流程图。",
            "plan_id": None, "status": "not_applicable",
        }],
    }
    plan_path = tmp_path / "visual-plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    result = visual_plan_audit.audit(plan_path, "plan", tmp_path, None)

    assert result["status"] == "PASS"
    assert result["summary"]["figures"] == 2
    assert result["summary"]["tables"] == 1
    assert not result["failures"]
