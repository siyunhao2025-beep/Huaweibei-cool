# -*- coding: utf-8 -*-
"""test_playbook_match.py — 题面→原型规则匹配正反例。

- 优化类题面 → top 原型应为 optimization，置信度 ≥0.5
- 预测类题面 → top 原型应为 prediction，置信度 ≥0.5
"""
import importlib.util


from conftest import PLAYBOOKS, SCRIPTS


def _load_match():
    spec = importlib.util.spec_from_file_location("pb_match", SCRIPTS / "playbook_match.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rules = mod.load_rules(PLAYBOOKS / "match_rules.json")
    return mod, rules


mod, RULES = _load_match()

OPTIMIZATION_PROMPT = (
    "某风电场需在满足疲劳损伤约束下，对多台机组做有功功率分配与实时调度，"
    "要求求最优出力组合，最小化发电成本与磨损代价，属于资源分配优化问题。"
)

PREDICTION_PROMPT = (
    "根据过去三年的历史风速与功率时序数据，外推并预测未来 24 小时的风功率趋势，"
    "为功率预测与电网调度提供依据。"
)


def test_optimization_prompt_matches_optimization():
    hits = mod.match(OPTIMIZATION_PROMPT, RULES)
    top = mod.pick_top(hits, RULES)
    assert top["archetype"] == "optimization", f"优化题面应命中 optimization，实际 {top}"
    assert top["confidence"] >= 0.5


def test_prediction_prompt_matches_prediction():
    hits = mod.match(PREDICTION_PROMPT, RULES)
    top = mod.pick_top(hits, RULES)
    assert top["archetype"] == "prediction", f"预测题面应命中 prediction，实际 {top}"
    assert top["confidence"] >= 0.5


def test_unknown_prompt_falls_back_to_human():
    hits = mod.match("今天天气不错，去散步。", RULES)
    top = mod.pick_top(hits, RULES)
    assert top["archetype"] == "unknown", f"无关键词命中应回退 unknown，实际 {top}"


def test_rules_file_has_all_eight_archetypes():
    prototypes = set(RULES.get("prototypes", []))
    assert {"optimization", "prediction", "evaluation", "simulation"} <= prototypes
    assert len(prototypes) == 8
