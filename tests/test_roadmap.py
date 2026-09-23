# -*- coding: utf-8 -*-
"""test_roadmap.py — 技术路线图体系测试。

覆盖：
  - schema 校验：合法 YAML 通过、非法 YAML 失败
  - 渲染烟雾：3 个 demo 都能渲染出 PNG 且非空白（>1KB）
  - 覆盖度正反例：完整 spec 通过 / 缺小问(映射落空)失败 / 孤立节点失败 / 非色盲安全色失败
  - 8 个原型模板全部通过 audit 并能渲染
  - 无中文字体时英文标签优雅回退不崩溃
  - --help 退出码 0
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, SCRIPTS

sys.path.insert(0, str(SCRIPTS))
import render_roadmap  # noqa: E402
import audit_roadmap  # noqa: E402

TEMPLATES = REPO_ROOT / "assets" / "roadmap" / "templates"
DEMOS = REPO_ROOT / "docs" / "examples" / "roadmap"
TEMPLATE_FILES = sorted(TEMPLATES.glob("*.yaml"))
DEMO_FILES = sorted(DEMOS.glob("*_demo.yaml"))


def base_spec() -> dict:
    """一个完整、合法、可通过全部校验的最小 spec。"""
    return {
        "metadata": {
            "title": "测试路线图",
            "year": 2026,
            "track": "DEMO",
            "version": "0.1.0",
            "feedback_expected": True,
        },
        "layers": [
            {"id": "input", "label": "输入", "order": 0},
            {"id": "preprocess", "label": "预处理", "order": 1},
            {"id": "model", "label": "模型", "order": 2},
            {"id": "solve", "label": "求解", "order": 3},
            {"id": "validate", "label": "验证", "order": 4},
            {"id": "output", "label": "输出", "order": 5},
        ],
        "nodes": [
            {"id": "n_data", "layer": "input", "label": "数据", "label_en": "Data", "method": "读取"},
            {"id": "n_pre", "layer": "preprocess", "label": "预处理", "label_en": "Pre", "method": "清洗"},
            {"id": "n_m", "layer": "model", "label": "模型", "label_en": "Model", "method": "SVM", "subquestion_ref": "Q1"},
            {"id": "n_s", "layer": "solve", "label": "求解", "label_en": "Solve", "method": "CV"},
            {"id": "n_v", "layer": "validate", "label": "验证", "label_en": "Valid", "method": "F1"},
            {"id": "n_o", "layer": "output", "label": "输出", "label_en": "Out", "method": "结论"},
        ],
        "edges": [
            {"from": "n_data", "to": "n_pre", "type": "solid"},
            {"from": "n_pre", "to": "n_m", "type": "solid"},
            {"from": "n_m", "to": "n_s", "type": "solid"},
            {"from": "n_s", "to": "n_v", "type": "solid"},
            {"from": "n_v", "to": "n_o", "type": "solid"},
            {"from": "n_v", "to": "n_m", "type": "dashed", "label": "迭代/调参"},
        ],
        "subquestion_mapping": {"Q1": ["n_m"]},
    }


def codes(result: dict) -> set[str]:
    return {c["code"] for c in result["checks"]}


def failed_codes(result: dict) -> set[str]:
    return {c["code"] for c in result["failures"]}


# ---------- schema 校验 ----------

def test_valid_spec_passes():
    r = audit_roadmap.audit(base_spec())
    assert r["status"] == "PASS", r["failures"]


def test_invalid_schema_fails():
    spec = base_spec()
    del spec["nodes"][2]["method"]  # 缺必填 method
    r = audit_roadmap.audit(spec)
    assert r["status"] == "FAIL"
    assert "schema_valid" in failed_codes(r)


# ---------- 覆盖度正反例 ----------

def test_missing_subquestion_fails():
    """Q2 映射到不存在的节点 → 小问落空，必须 FAIL 并点名 Q2。"""
    spec = base_spec()
    spec["subquestion_mapping"]["Q2"] = ["n_not_exist"]
    r = audit_roadmap.audit(spec)
    assert r["status"] == "FAIL"
    assert "subquestion_node_exists" in failed_codes(r)
    ghost = next(c for c in r["failures"] if c["code"] == "subquestion_node_exists")
    assert "Q2" in ghost["ghost"]


def test_isolated_node_fails():
    """中间层新增一个无边节点 → 孤立节点 FAIL。"""
    spec = base_spec()
    spec["nodes"].append({"id": "n_lonely", "layer": "solve", "label": "孤节点", "method": "X"})
    r = audit_roadmap.audit(spec)
    assert r["status"] == "FAIL"
    assert "no_isolated_node" in failed_codes(r) or "no_isolated_nodes" in failed_codes(r)
    iso = next(c for c in r["failures"] if "isolated" in c["code"])
    assert "n_lonely" in iso["isolated"]


def test_unsafe_color_fails():
    """节点用了非色盲安全色（tab:blue）→ cbf_safe_colors FAIL。"""
    spec = base_spec()
    spec["nodes"][2]["color"] = "tab:blue"
    r = audit_roadmap.audit(spec)
    assert r["status"] == "FAIL"
    assert "cbf_safe_colors" in failed_codes(r)


def test_no_feedback_is_valid_when_policy_declares_none():
    spec = base_spec()
    spec["metadata"]["feedback_expected"] = False
    spec["edges"] = [edge for edge in spec["edges"] if edge["type"] != "dashed"]

    result = audit_roadmap.audit(spec)

    assert result["status"] == "PASS", result["failures"]


def test_feedback_policy_rejects_invented_dashed_edge():
    spec = base_spec()
    spec["metadata"]["feedback_expected"] = False

    result = audit_roadmap.audit(spec)

    assert result["status"] == "FAIL"
    assert "feedback_policy_match" in failed_codes(result)


# ---------- 8 个模板 ----------

def test_eight_templates_pass_audit():
    assert len(TEMPLATE_FILES) == 8, f"应正好 8 个原型模板，实得 {len(TEMPLATE_FILES)}"
    for f in TEMPLATE_FILES:
        spec = render_roadmap.load_spec(f)
        r = audit_roadmap.audit(spec)
        assert r["status"] == "PASS", f"{f.name} 未通过校验: {r['failures']}"


def test_eight_templates_render(tmp_path):
    for f in TEMPLATE_FILES:
        spec = render_roadmap.load_spec(f)
        out = render_roadmap.render(spec, tmp_path / f.stem, ["png"])
        png = Path(out["written"]["png"])
        assert png.is_file() and png.stat().st_size > 1024, f"{f.name} 渲染 PNG 异常"


# ---------- 3 个 demo 渲染烟雾 ----------

@pytest.mark.parametrize("demo", DEMO_FILES, ids=lambda p: p.name)
def test_demo_renders_nonempty_png(demo, tmp_path):
    spec = render_roadmap.load_spec(demo)
    out = render_roadmap.render(spec, tmp_path / demo.stem, ["png", "pdf", "mmd", "dot"])
    png = Path(out["written"]["png"])
    pdf = Path(out["written"]["pdf"])
    assert png.stat().st_size > 1024, f"{demo.name} PNG 过小/空白"
    assert pdf.is_file() and pdf.stat().st_size > 1024
    assert Path(out["written"]["mmd"]).is_file()
    assert Path(out["written"]["dot"]).is_file()


# ---------- 无中文字体回退 ----------

def test_no_cjk_font_fallback(monkeypatch, tmp_path):
    """模拟系统无任何 CJK 字体：应切 label_en 英文回退，不崩溃。"""
    monkeypatch.setattr(render_roadmap, "detect_cjk_font", lambda: (None, False))
    out = render_roadmap.render(base_spec(), tmp_path / "fallback", ["png"])
    png = Path(out["written"]["png"])
    assert png.is_file() and png.stat().st_size > 1024
    assert out["has_cjk_font"] is False


# ---------- CLI ----------

def test_help_exit_zero():
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "render_roadmap.py"), "--help"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 0, r.stderr
