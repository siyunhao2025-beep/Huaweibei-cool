# -*- coding: utf-8 -*-
"""test_figure_smoke.py — academic-figure skill 结构与中文字体烟雾测试。

- SKILL.md 存在
- scripts/ 目录有可运行脚本
- assets/figure-atlas 有 PNG 参考图
- 中文字体：尝试用 matplotlib 检测系统 CJK 字体；不可用则 skip 并标注
"""
from pathlib import Path

import pytest

from conftest import REPO_ROOT

FIG = REPO_ROOT / "skills" / "academic-figure"


def test_skill_md_exists():
    assert (FIG / "SKILL.md").is_file(), "缺 SKILL.md"


def test_scripts_dir_has_runnable_scripts():
    scripts_dir = FIG / "scripts"
    assert scripts_dir.is_dir(), "缺 scripts/ 目录"
    pys = list(scripts_dir.glob("*.py"))
    assert pys, "scripts/ 下无可运行 .py 脚本"


def test_figure_atlas_has_pngs():
    atlas = FIG / "assets" / "figure-atlas"
    if not atlas.is_dir():
        pytest.skip("figure-atlas 目录不存在（可能被 gitignore，需现场确认结构说明）")
    pngs = list(atlas.glob("*.png"))
    assert pngs, "figure-atlas 下无 PNG 参考图"


def test_chinese_font_available():
    """检测系统中文字体是否可用；不可用则跳过并标注（不失败）。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import font_manager
    except Exception as e:
        pytest.skip(f"未现场验证中文字体渲染：matplotlib 不可用 ({e})")
    cjk_keywords = ("Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK",
                    "Source Han", "WenQuanYi", "DengXian", "KaiTi", "FangSong")
    installed = {f.name for f in font_manager.fontManager.ttflist}
    hit = [n for n in installed if any(k.lower() in n.lower() for k in cjk_keywords)]
    if not hit:
        pytest.skip("未现场验证中文字体渲染：系统未检出常见 CJK 字体")
    # 记录可用字体，供 figure skill 选用
    assert hit, hit
