#!/usr/bin/env python3
"""Static and rendered QA gate for Chinese scientific figure text."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from chinese_fonts import inspect_image

CJK_RE = re.compile(r"[\u3400-\u9fff]")
PY_FONT_MARKERS = ("FontProperties", "find_chinese_font", "font_manager")
R_FONT_MARKERS = ("systemfonts", "sysfonts", "showtext", "font_add")


def _read(target: str) -> tuple[str, str]:
    if os.path.isfile(target):
        path = Path(target)
        return path.read_text(encoding="utf-8", errors="replace"), path.suffix.lower()
    return target, ""


def check(target, journal="nature-genetics"):
    source, suffix = _read(target)
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        result = inspect_image(Path(target))
        return "Chinese glyph render", bool(result.get("ok")), [str(result)]
    if suffix == ".pdf":
        ok = Path(target).is_file() and Path(target).stat().st_size > 0
        messages = ["PDF exists" if ok else "PDF missing or empty"]
        if ok and shutil.which("pdftotext"):
            extracted = subprocess.run(["pdftotext", "-layout", target, "-"], capture_output=True, text=True,
                                       encoding="utf-8", errors="replace", check=False).stdout
            has_cjk = bool(CJK_RE.search(extracted))
            messages.append("PDF contains extractable Chinese glyph text" if has_cjk else
                            "FAIL: PDF has no extractable Chinese glyph text")
            ok = ok and has_cjk
        return "Chinese glyph render", ok, messages

    messages = []
    has_cjk = bool(CJK_RE.search(source))
    if not has_cjk:
        messages.append("FAIL: ordinary result-figure display text must include Chinese labels/captions")
    is_python = suffix in {".py", ""} and ("matplotlib" in source or "plt." in source or "fig," in source)
    is_r = suffix in {".r", ".rmd", ".qmd"} or "ggplot(" in source
    if is_python:
        if not any(marker in source for marker in PY_FONT_MARKERS):
            messages.append("FAIL: Python figure must resolve an installed Chinese font and use FontProperties/fallback")
        if not re.search(r"unicode_minus[\"']?\s*(?:\])?\s*[\"']?\s*[:=]\s*False", source):
            messages.append("FAIL: Python figure must set axes.unicode_minus=False")
        if not re.search(r"canvas\.draw\s*\(", source):
            messages.append("FAIL: Python figure must call fig.canvas.draw() before export")
    if is_r:
        if not any(marker in source for marker in R_FONT_MARKERS):
            messages.append("FAIL: R figure must detect fonts with systemfonts/sysfonts/showtext")
        if not re.search(r"(?:png\s*\([^)]*type\s*=\s*['\"]cairo|cairo_pdf\s*\()", source, re.I | re.S):
            messages.append("FAIL: R figure must use Cairo rendering for PNG/PDF")
    passed = has_cjk and not any(message.startswith("FAIL:") for message in messages)
    if passed:
        messages.append("PASS: Chinese labels, font resolution, minus-sign and draw/render gate detected")
    return "Chinese text/font QA", passed, messages


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    args = parser.parse_args()
    name, passed, messages = check(args.target)
    print(name)
    print("\n".join(messages))
    raise SystemExit(0 if passed else 1)
