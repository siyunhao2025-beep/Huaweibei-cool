# -*- coding: utf-8 -*-
"""test_progress_gate.py — P0-P6 内容级门禁正反例测试。

重点（反 AI 读题审计硬门禁）：
  - 空目录 → P0 FAIL
  - 有题面/原型记录但【无用户确认记录】→ P1 FAIL（不得进入求解）
  - 有 evidence-ledger.json 且 user_confirmation=true → P1 PASS
  - 有 markdown 台账且含确认标记 → P1 PASS
  - 模型假设 ≥3 条 + 目标函数 + 求解脚本 → P2 PASS
"""
import json
import sys
from pathlib import Path

import pytest

from conftest import SCRIPTS


def _load_progress():
    import importlib.util
    spec = importlib.util.spec_from_file_location("progress_mod", SCRIPTS / "progress.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


prog = _load_progress()


def test_empty_dir_p0_fail(tmp_path):
    passed, _ = prog.check_phase("P0", tmp_path)
    assert passed is False, "空目录 P0 必须 FAIL"


def _seed_reading_audit(root: Path):
    """写入题面约束/拆解 + 原型判定记录（但不放用户确认记录）。"""
    (root / "题目").mkdir(exist_ok=True)
    (root / "题目" / "题面.txt").write_text(
        "风电场有功功率分配。约束：疲劳损伤上限。问题分析：需做功率分配优化拆解。",
        encoding="utf-8")
    (root / "原型判定.md").write_text(
        "题型判定：主原型 optimization，辅 prediction。", encoding="utf-8")
    (root / "contest.json").write_text("{}", encoding="utf-8")


def test_p1_fails_without_user_confirmation(tmp_path):
    _seed_reading_audit(tmp_path)
    passed, items = prog.check_phase("P1", tmp_path)
    assert passed is False, "无用户确认记录时 P1 必须 FAIL（反AI硬门禁）"
    descs = " ".join(d for _, d in items)
    assert "确认" in descs, "P1 检查项应包含用户确认记录检查"


def test_p1_passes_with_json_confirmation(tmp_path):
    _seed_reading_audit(tmp_path)
    (tmp_path / "evidence-ledger.json").write_text(
        json.dumps({"user_confirmation": True, "裁决": "认可优化路线"}, ensure_ascii=False),
        encoding="utf-8")
    passed, _ = prog.check_phase("P1", tmp_path)
    assert passed is True, "有 evidence-ledger.json/user_confirmation=true 时 P1 应 PASS"


def test_p1_passes_with_markdown_ledger(tmp_path):
    _seed_reading_audit(tmp_path)
    (tmp_path / "题目" / "evidence-ledger.md").write_text(
        "# 证据台账\n用户已确认：认可主原型与图表计划，裁决已记录。\n",
        encoding="utf-8")
    passed, _ = prog.check_phase("P1", tmp_path)
    assert passed is True, "markdown 台账含确认标记时 P1 应 PASS"


def test_p2_passes_with_three_assumptions(tmp_path):
    (tmp_path / "求解").mkdir()
    (tmp_path / "求解" / "model.py").write_text("print('baseline')", encoding="utf-8")
    (tmp_path / "求解" / "假设.md").write_text(
        "模型假设：\n"
        "1. 假设所有风机出力可独立调节\n"
        "2. 假设风功率预测误差服从正态分布\n"
        "3. 假设疲劳损伤按线性雨流累积\n"
        "目标函数：min 总疲劳代价 s.t. 功率平衡\n",
        encoding="utf-8")
    passed, items = prog.check_phase("P2", tmp_path)
    assert passed is True, f"≥3条假设+目标函数+求解脚本时 P2 应 PASS，items={items}"


def test_p2_fails_with_too_few_assumptions(tmp_path):
    (tmp_path / "求解").mkdir()
    (tmp_path / "求解" / "model.py").write_text("print('x')", encoding="utf-8")
    (tmp_path / "求解" / "假设.md").write_text(
        "模型假设：\n1. 假设风机出力可独立调节\n", encoding="utf-8")
    passed, _ = prog.check_phase("P2", tmp_path)
    assert passed is False, "假设<3条时 P2 必须 FAIL"
