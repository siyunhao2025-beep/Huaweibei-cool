#!/usr/bin/env python3
"""Resolve and smoke-test an installed Chinese-capable matplotlib font.

The resolver deliberately verifies glyph coverage instead of trusting a font
family name.  This prevents matplotlib's silent fallback from turning Chinese
labels into tofu boxes or an English-only fallback.
"""
from __future__ import annotations

import argparse
import json
import logging
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_GLYPHS = "中文测量单位预测残差模型基线改进值"


@dataclass(frozen=True)
class FontInfo:
    path: str
    family: str
    glyphs_checked: str


def _font_paths() -> list[Path]:
    from matplotlib import font_manager

    paths = [Path(p) for p in font_manager.findSystemFonts()]
    if not paths:
        paths = [Path(p) for p in font_manager.findSystemFonts(fontext="ttf")]
    known = [
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
        Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
        Path(r"/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path(r"/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    ]
    ordered = []
    seen = set()
    for path in known + paths:
        key = str(path).lower()
        if key not in seen and path.is_file():
            seen.add(key)
            ordered.append(path)
    return ordered


def _supports(path: Path, glyphs: str) -> bool:
    from matplotlib.ft2font import FT2Font

    try:
        face = FT2Font(str(path))
        return all(face.get_char_index(ord(char)) for char in glyphs)
    except (OSError, RuntimeError, ValueError):
        return False


def find_chinese_font(glyphs: str = REQUIRED_GLYPHS) -> FontInfo | None:
    """Return a real installed font with every requested glyph, if any."""
    from matplotlib.font_manager import FontProperties

    for path in _font_paths():
        if _supports(path, glyphs):
            family = FontProperties(fname=str(path)).get_name()
            return FontInfo(str(path), family, glyphs)
    return None


def configure_matplotlib(font: FontInfo | None = None):
    """Configure Chinese-capable defaults and return the selected FontInfo."""
    import matplotlib as mpl

    selected = font or find_chinese_font()
    if selected is None:
        raise RuntimeError("没有检测到覆盖所需中文字符的已安装字体")
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [selected.family, "Arial", "Helvetica", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    })
    return selected


def inspect_image(path: Path) -> dict:
    """Check that a rendered raster exists, has dimensions, and is nonblank."""
    from PIL import Image, ImageChops, ImageStat

    if not path.is_file() or path.stat().st_size == 0:
        return {"path": str(path), "ok": False, "error": "输出文件不存在或为空"}
    try:
        image = Image.open(path).convert("RGB")
        gray = image.convert("L")
        variance = ImageStat.Stat(gray).var[0]
        ink = ImageChops.difference(gray, Image.new("L", gray.size, 255)).getbbox()
        margin = min(ink[0], ink[1], image.width - ink[2], image.height - ink[3]) if ink else 0
        checks = {
            "nonblank": variance > 0.1 and bool(ink),
            "scaling": image.width >= 300 and image.height >= 200,
            "clipping": margin >= 2,
            "grayscale": variance > 5,
            # Text/marker overlap still needs a visual pass; keep it explicit
            # in the report instead of pretending pixel heuristics can prove it.
            "overlap": "manual_visual_review_required",
        }
        return {"path": str(path), "ok": all(value is True for key, value in checks.items() if key != "overlap"),
                "size": [image.width, image.height], "variance": variance, "margin": margin, "checks": checks}
    except Exception as exc:  # pragma: no cover - Pillow backend dependent
        return {"path": str(path), "ok": False, "error": str(exc)}


def render_smoke_test(output_dir: Path) -> dict:
    """Render Chinese labels, units, RMSE, negatives, Greek and subscripts."""
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties

    output_dir.mkdir(parents=True, exist_ok=True)
    selected = find_chinese_font()
    if selected is None:
        return {"status": "INCOMPLETE", "error": "缺少可覆盖中文字符的字体"}
    configure_matplotlib(selected)
    prop = FontProperties(fname=selected.path)
    fig, ax = plt.subplots(figsize=(4.2, 2.8), dpi=120)
    ax.plot([-1.0, -0.25, 0.5, 1.0], [0.2, -0.1, 0.35, 0.05], label="基线模型", color="#2166AC")
    ax.plot([-1.0, -0.25, 0.5, 1.0], [0.1, -0.2, 0.25, 0.12], label="改进模型", color="#B2182B")
    ax.set_title("中文显示测试", fontproperties=prop)
    ax.set_xlabel("预测值（单位）", fontproperties=prop)
    ax.set_ylabel("残差 / RMSE", fontproperties=prop)
    ax.legend(prop=prop, frameon=False)
    # Mathtext supplies a portable subscript while the surrounding Chinese
    # annotation remains in the verified CJK font.
    ax.text(0.03, 0.92, r"RMSE = 0.123；α$_1$ = −0.25", transform=ax.transAxes,
            fontproperties=prop, va="top")
    ax.set_xticks([-1, 0, 1])
    ax.set_xticklabels(["−1", "0", "1"], fontproperties=prop)
    ax.set_yticks([-0.2, 0, 0.4])
    ax.set_yticklabels(["−0.2", "0", "0.4"], fontproperties=prop)
    # A draw is mandatory: savefig alone can miss glyph/layout failures.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.canvas.draw()
        draw_warnings = [str(item.message) for item in caught if "Glyph" in str(item.message)]
    png = output_dir / "chinese_font_smoke.png"
    pdf = output_dir / "chinese_font_smoke.pdf"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fig.savefig(png, dpi=300, bbox_inches="tight")
        fig.savefig(pdf, bbox_inches="tight")
        draw_warnings.extend(str(item.message) for item in caught if "Glyph" in str(item.message))
    plt.close(fig)
    image_check = inspect_image(png)
    status = "PASS" if image_check["ok"] and pdf.stat().st_size > 0 and not draw_warnings else "INCOMPLETE"
    return {"status": status,
            "font": asdict(selected), "png": image_check, "pdf": {"path": str(pdf), "ok": pdf.stat().st_size > 0},
            "glyph_warnings": sorted(set(draw_warnings))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("figure_font_smoke"))
    args = parser.parse_args()
    result = render_smoke_test(args.output_dir) if args.smoke_test else (
        {"status": "PASS", "font": asdict(find_chinese_font())} if find_chinese_font()
        else {"status": "INCOMPLETE", "error": "没有可用中文字体"}
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
