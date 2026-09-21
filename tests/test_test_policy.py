# -*- coding: utf-8 -*-
"""测试政策：不允许用 skip/xfail 掩盖未完成验证。"""
from pathlib import Path


TESTS = Path(__file__).resolve().parent
FORBIDDEN = (
    "pytest.skip(",
    "pytest.xfail(",
    "pytest.importorskip(",
    "@pytest.mark.skip",
    "@pytest.mark.xfail",
    "@unittest.skip",
)


def test_suite_has_no_skip_or_xfail_escape_hatches():
    offenders = []
    for path in TESTS.glob("*.py"):
        if path == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        offenders.extend((path.name, token) for token in FORBIDDEN if token in text)
    assert not offenders, f"禁止跳过或预期失败：{offenders}"
