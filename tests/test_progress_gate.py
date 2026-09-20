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


# --- 优秀论文自检表门禁（Wave6-B）正反例 ---

def _seed_p4_base(root: Path):
    """写出一份含摘要/结论/主要章节的论文正文（不含自检表）。"""
    (root / "论文").mkdir(exist_ok=True)
    (root / "论文" / "paper.md").write_text(
        "摘要：本文做了功率分配。\n模型假设：...\n问题重述：...\n参考文献：[1]\n结论：完成。\n",
        encoding="utf-8")


def test_p4_fails_without_checklist(tmp_path):
    _seed_p4_base(tmp_path)
    passed, items = prog.check_phase("P4", tmp_path)
    assert passed is False, "无自检表文件时 P4 必须 FAIL"
    descs = " ".join(d for _, d in items)
    assert "自检表" in descs, "P4 应含自检表存在性检查"


def test_p4_passes_with_checklist(tmp_path):
    _seed_p4_base(tmp_path)
    (tmp_path / "论文" / "优秀论文自检表.md").write_text(
        "# 优秀论文自检表\n- [ ] A01 ...\n", encoding="utf-8")
    passed, items = prog.check_phase("P4", tmp_path)
    assert passed is True, f"有自检表文件时 P4 应 PASS，items={items}"


def _seed_p6_base(root: Path):
    """写出 P6 必需的附件/AI披露/PDF（不含自检表闭环产物）。"""
    (root / "提交附件").mkdir(exist_ok=True)
    (root / "提交附件" / "solve.m").write_text("disp('ok');", encoding="utf-8")
    (root / "论文").mkdir(exist_ok=True)
    (root / "论文" / "paper.txt").write_text(
        "本文使用了AI工具辅助数据分析与编程。\n参考文献：[1]\n", encoding="utf-8")
    (root / "论文" / "paper.pdf").write_bytes(b"%PDF-1.4 fake")


def test_p6_fails_without_checked_table(tmp_path):
    _seed_p6_base(tmp_path)
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False, "无《论文自检表_已勾选.md》时 P6 必须 FAIL"
    descs = " ".join(d for _, d in items)
    assert "已勾选" in descs, "P6 应含已勾选自检表落盘检查"


def test_p6_fails_when_sidecar_missing(tmp_path):
    _seed_p6_base(tmp_path)
    (tmp_path / "论文" / "论文自检表_已勾选.md").write_text(
        "# 论文自检表（已勾选）\n- [x] A01 ...\n", encoding="utf-8")
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False, "缺 sidecar（待运行 paper_checklist）时 P6 必须 FAIL"
    descs = " ".join(d for _, d in items)
    assert "待运行 paper_checklist" in descs, "缺 sidecar 应提示待运行 paper_checklist"


def test_p6_fails_when_sidecar_has_undecided(tmp_path):
    _seed_p6_base(tmp_path)
    (tmp_path / "论文" / "论文自检表_已勾选.md").write_text(
        "# 论文自检表（已勾选）\n", encoding="utf-8")
    (tmp_path / "论文" / "paper_checklist_decisions.json").write_text(
        json.dumps({"decisions": [
            {"id": "A01", "status": "passed"},
            {"id": "A02", "status": "pending"},
        ]}, ensure_ascii=False), encoding="utf-8")
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is False, "sidecar 含未裁决人工条目时 P6 必须 FAIL"


def test_p6_passes_with_checked_table_and_clean_sidecar(tmp_path):
    _seed_p6_base(tmp_path)
    (tmp_path / "论文" / "论文自检表_已勾选.md").write_text(
        "# 论文自检表（已勾选）\n- [x] A01 ...\n", encoding="utf-8")
    (tmp_path / "论文" / "paper_checklist_decisions.json").write_text(
        json.dumps({"decisions": [
            {"id": "A01", "status": "passed"},
            {"id": "A02", "status": "na", "reason": "本题不适用"},
        ]}, ensure_ascii=False), encoding="utf-8")
    passed, items = prog.check_phase("P6", tmp_path)
    assert passed is True, f"已勾选表落盘 + sidecar 无未裁决项时 P6 应 PASS，items={items}"
