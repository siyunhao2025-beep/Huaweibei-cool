# -*- coding: utf-8 -*-
"""test_figure_smoke.py — academic-figure skill 结构与中文字体烟雾测试。

- SKILL.md 存在
- scripts/ 目录有可运行脚本
- assets/figure-atlas 有 PNG 参考图
- 中文字体：用 matplotlib 检测系统 CJK 字体；不可用就真实失败
"""
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
    assert atlas.is_dir(), "缺 figure-atlas 目录"
    pngs = list(atlas.glob("*.png"))
    assert pngs, "figure-atlas 下无 PNG 参考图"


def test_chinese_font_available():
    """检测系统中文字体是否可用；缺依赖或字体都必须失败。"""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import font_manager

    cjk_keywords = ("Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK",
                    "Source Han", "WenQuanYi", "DengXian", "KaiTi", "FangSong")
    installed = {f.name for f in font_manager.fontManager.ttflist}
    hit = [n for n in installed if any(k.lower() in n.lower() for k in cjk_keywords)]
    assert hit, "系统未检出常见 CJK 字体"
