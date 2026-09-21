# -*- coding: utf-8 -*-
"""一键演示脚本的轻量回归检查。"""
from conftest import REPO_ROOT


QUICKSTART = REPO_ROOT / "scripts" / "quickstart_demo.ps1"


def test_quickstart_forces_utf8_for_chinese_output():
    text = QUICKSTART.read_text(encoding="utf-8")
    assert '$env:PYTHONUTF8 = "1"' in text
    assert "[Console]::OutputEncoding = $Utf8NoBom" in text
    assert "$OutputEncoding = $Utf8NoBom" in text
