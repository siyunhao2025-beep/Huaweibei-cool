# -*- coding: utf-8 -*-
"""test_card_schemas.py — 卡片 JSON Schema 合规性测试。

- 加载 corpus/schemas/ 下 brief/deep/playbook/track 四个 schema
- 用 jsonschema 校验全部 729 张 brief 卡、80 张 deep 卡
- playbook/track schema 仅校验其本身是合法 JSON Schema

说明：全部 729 张 brief 卡与 80 张 deep 卡必须零违例（历史上 2 张 deep 卡
违例已于交付复核时修复，不再保留豁免清单）。
"""
import glob
import json
from pathlib import Path

import pytest

from conftest import CORPUS, REPO_ROOT

SCHEMAS = CORPUS / "schemas"


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


def test_deep_cards_all_valid(deep_validator):
    files = sorted(glob.glob(str(CORPUS / "cards" / "deep" / "*.json")))
    assert len(files) == 80, f"deep 卡数量 {len(files)} != 80"
    bad = []
    for f in files:
        c = json.load(open(f, encoding="utf-8"))
        for err in deep_validator.iter_errors(c):
            bad.append((c.get("paper_id"), list(err.path), err.message))
    assert not bad, f"deep 卡 schema 违例（前10）: {bad[:10]}"
