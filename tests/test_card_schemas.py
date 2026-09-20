# -*- coding: utf-8 -*-
"""test_card_schemas.py — 卡片 JSON Schema 合规性测试。

- 加载 corpus/schemas/ 下 brief/deep/playbook/track 四个 schema
- 用 jsonschema 校验全部 729 张 brief 卡、80 张 deep 卡
- playbook/track schema 仅校验其本身是合法 JSON Schema

说明：经 Wave3 预检，有 2 张 deep 卡存在已知 schema 违例（知识产物，
按工程纪律不改卡片，仅登记为 KNOWN_DEEP_VIOLATIONS 供后续 Wave 修复）。
本测试断言：违例集合 ⊆ 已知集合，即不允许出现新增违例。
"""
import glob
import json
from pathlib import Path

import pytest

from conftest import CORPUS, REPO_ROOT

SCHEMAS = CORPUS / "schemas"

# 已知 deep 卡违例（paper_id, 违例字段路径）——Wave2B 待修，工程验证不改卡片
KNOWN_DEEP_VIOLATIONS = {
    ("2009_X_论文1042215B 最终", ("page_locations",)),
    ("2022_C_C22103560098", ("independent_validation_design",)),
}


def _load_validator(schema_file):
    from jsonschema import Draft202012Validator
    schema = json.load(open(schema_file, encoding="utf-8"))
    return Draft202012Validator(schema)


@pytest.fixture(scope="module")
def brief_validator():
    return _load_validator(SCHEMAS / "brief-card.schema.json")


@pytest.fixture(scope="module")
def deep_validator():
    return _load_validator(SCHEMAS / "deep-card.schema.json")


def test_all_four_schemas_parse():
    """四个 schema 文件都能被解析为合法 JSON Schema。"""
    from jsonschema import Draft202012Validator
    for name in ("brief-card", "deep-card", "playbook-card", "track-card"):
        path = SCHEMAS / f"{name}.schema.json"
        assert path.is_file(), f"缺 schema: {path}"
        schema = json.load(open(path, encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


def test_brief_cards_all_valid(brief_validator):
    cards = []
    for f in sorted(glob.glob(str(CORPUS / "cards" / "brief" / "*.json"))):
        cards.extend(json.load(open(f, encoding="utf-8")))
    assert len(cards) == 729, f"brief 卡数量 {len(cards)} != 729"
    bad = []
    for c in cards:
        for err in brief_validator.iter_errors(c):
            bad.append((c.get("paper_id"), list(err.path), err.message))
    assert not bad, f"brief 卡 schema 违例（前10）: {bad[:10]}"


def test_deep_cards_valid_except_known(deep_validator):
    files = sorted(glob.glob(str(CORPUS / "cards" / "deep" / "*.json")))
    assert len(files) == 80, f"deep 卡数量 {len(files)} != 80"
    violations = set()
    for f in files:
        c = json.load(open(f, encoding="utf-8"))
        for err in deep_validator.iter_errors(c):
            violations.add((c.get("paper_id"), tuple(err.path)))
    new_violations = violations - KNOWN_DEEP_VIOLATIONS
    assert not new_violations, f"发现新增 deep 卡 schema 违例: {sorted(new_violations)}"
    # 同时确认已知违例仍在（防止被静默当作已修）
    missing_known = KNOWN_DEEP_VIOLATIONS - violations
    if missing_known:
        pytest.skip(f"已知违例疑似已被修复，可从 KNOWN_DEEP_VIOLATIONS 移除: {missing_known}")
