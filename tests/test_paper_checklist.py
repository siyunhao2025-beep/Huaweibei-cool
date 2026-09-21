# -*- coding: utf-8 -*-
"""test_paper_checklist.py — Wave6-A 自检表机检脚本与资产测试。"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ASSETS, REPO_ROOT, SCRIPTS

CHECKLIST_JSON = ASSETS / "checklists" / "paper_checklist.json"
CHECKLIST_MD = ASSETS / "checklists" / "优秀论文自检表.md"
PASS_TEX = Path(__file__).resolve().parent / "fixtures" / "checklist_pass.tex"
FAIL_TEX = Path(__file__).resolve().parent / "fixtures" / "checklist_fail.tex"
SCRIPT = SCRIPTS / "paper_checklist.py"


def _run(args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd or REPO_ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )


# --------------------------------------------------------------------------- #
# 资产
# --------------------------------------------------------------------------- #
def test_checklist_json_parseable_and_138():
    d = json.loads(CHECKLIST_JSON.read_text(encoding="utf-8"))
    assert d["total"] == 138
    assert len(d["items"]) == 138
    ids = [it["id"] for it in d["items"]]
    assert len(set(ids)) == 138, "id 必须唯一"
    # 关键章节齐全
    sections = {it["section"] for it in d["items"]}
    for sec in ["全局格式", "摘要", "模型求解", "参考文献"]:
        assert sec in sections
    # 旧截图的三处转录记录已闭合；当前语义由纠错后的 item 字段承载。
    notes = {it["id"]: it.get("notes") for it in d["items"]}
    assert notes["M14"] is None
    assert notes["I02"] is None
    assert notes["V05"] is None
    by_id = {it["id"]: it for it in d["items"]}
    assert "服从数据结构" in by_id["V05"]["item"]
    assert by_id["V05"]["applicable_archetypes"] == [
        "classification-cv", "prediction", "spatial-graph"
    ]
    for sid in ["B12", "H04", "H05", "Q02", "Q09", "E01", "E03", "E05", "R02"]:
        assert by_id[sid]["check_method"] == "manual"


def test_checklist_md_exists_and_has_execution_requirements():
    txt = CHECKLIST_MD.read_text(encoding="utf-8")
    assert "## 执行要求" in txt
    assert "全量闭环" in txt
    assert "不等于强行让 138 项全部通过" in txt
    # 不得出现具体商业 AI 产品名
    for banned in ["claude", "chatgpt", "Claude", "ChatGPT"]:
        assert banned not in txt
    # 138 条勾选行
    assert txt.count("- [ ] ") == 138


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_help_exit_zero():
    p = _run(["--help"])
    assert p.returncode == 0, p.stderr


# --------------------------------------------------------------------------- #
# 正例 fixture
# --------------------------------------------------------------------------- #
def test_pass_fixture_zero_fail(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    p = _run(["--tex", str(PASS_TEX), "--problems", "2",
              "--archetype", "optimization", "--outdir", str(outdir)])
    assert p.returncode == 0, f"pass fixture 应退出 0，实际 {p.returncode}\n{p.stdout}\n{p.stderr}"
    report = (outdir / "论文自检表_已勾选.md").read_text(encoding="utf-8")
    # 机检条目全 ✅：不应有任何 "- ❌" 行（统计行里的 "❌ N" 不算）
    fail_lines = [ln for ln in report.splitlines() if ln.startswith("- ❌")]
    assert not fail_lines, f"正例 fixture 不应有 ❌：{fail_lines}"
    # 关键机检项
    for sid in ["Q03", "Q04", "S03", "S04", "A02", "A10", "V04"]:
        assert f"✅ **{sid}**" in report, f"正例 {sid} 应 ✅"


# --------------------------------------------------------------------------- #
# 反例 fixture
# --------------------------------------------------------------------------- #
def test_fail_fixture_detects_all_planted_errors(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    p = _run(["--tex", str(FAIL_TEX), "--problems", "2",
              "--archetype", "optimization", "--outdir", str(outdir)])
    assert p.returncode == 1, f"fail fixture 应退出 1，实际 {p.returncode}"
    report = (outdir / "论文自检表_已勾选.md").read_text(encoding="utf-8")
    # 每个故意埋的错误至少对应一条 ❌
    expected = {
        "Q04": "图表未引用",
        "Q03": "纯英文题注",
        "V04": "优化检验缺少适配证据",
    }
    for sid, why in expected.items():
        assert f"❌ **{sid}**" in report, f"反例应检出 {sid}（{why}）"
    for retired_false_positive in ["R02", "Q02", "Q09", "H05", "E03"]:
        assert f"❌ **{retired_false_positive}**" not in report


# --------------------------------------------------------------------------- #
# sidecar 与 --strict
# --------------------------------------------------------------------------- #
def test_mark_persists_and_strict_gate(tmp_path):
    outdir = tmp_path / "out"
    outdir.mkdir()
    # 先跑一次，此时人工条目未裁决，--strict 应失败
    p = _run(["--tex", str(PASS_TEX), "--problems", "2",
              "--archetype", "optimization", "--outdir", str(outdir), "--strict"])
    assert p.returncode == 1, "未裁决人工条目时 --strict 应失败"
    # --mark 一批人工条目
    p = _run(["--tex", str(PASS_TEX), "--outdir", str(outdir),
              "--mark", "F01=pass", "--mark", "F02=pass", "--mark", "F03=pass",
              "--mark", "F04=pass", "--mark", "F05=pass", "--mark", "F06=pass",
              "--mark", "T06=pass", "--mark", "Q08=na", "--note", "全部图表均有正文引用"])
    assert p.returncode == 0, p.stderr
    dec = json.loads((outdir / "paper_checklist_decisions.json").read_text(encoding="utf-8"))
    assert dec["F01"]["status"] == "pass"
    assert dec["Q08"]["status"] == "na"
    assert "图表" in dec["Q08"]["note"]


# --------------------------------------------------------------------------- #
# contest_init 集成
# --------------------------------------------------------------------------- #
def test_contest_init_copies_checklist(tmp_path, monkeypatch):
    import contest_init
    workdir = tmp_path / "work"
    contest_init.init_workdir(workdir)
    target = workdir / "论文" / "优秀论文自检表.md"
    assert target.exists(), f"contest_init 未复制自检表到 {target}"
    config = workdir / "config" / "contest.json"
    assert config.exists(), f"contest_init 未复制比赛配置到 {config}"
    data = json.loads(config.read_text(encoding="utf-8"))
    assert data["paper"]["internal_total_page_target"]["mode"] == "user_decides"
    assert "执行要求" in target.read_text(encoding="utf-8")
