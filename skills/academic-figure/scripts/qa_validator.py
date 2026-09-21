#!/usr/bin/env python3
"""Academic Figure Skill QA Validator — translates references/checklist.md into executable assertions.

Input:  a generated Python plot script (or inline code string)
Output: structured PASS/FAIL/WARN report with line-level issue locations.

Usage:
    python qa_validator.py <script.py>              # validate a file
    python qa_validator.py "<code string>"          # validate inline code

Checks: AP-0 through AP-7, CL-1 through CL-7 (≈20 automated checks).
Pass 2 (VI-1..VI-6) and Pass 3 (VV-1..VV-5) are LLM-executed per checklist.md.
No AI needed for automated checks — runs anywhere Python is installed.
"""

from __future__ import annotations
import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Finding:
    check_id: str
    pass_: bool
    category: str  # "PASS", "FAIL", "WARN"
    message: str
    line: int | None = None  # best-effort line number


def _rc_setting(source: str, key: str, value_pattern: str) -> bool:
    """Match a matplotlib rcParams key in dict or indexed-assignment form."""
    quoted_key = rf'["\']{re.escape(key)}["\']'
    pattern = rf'{quoted_key}\s*(?::|\]\s*=)\s*{value_pattern}'
    return bool(re.search(pattern, source, re.IGNORECASE))


def _has_vector_export(source: str) -> bool:
    return bool(
        re.search(r'(?:savefig|ggsave)\s*\([^\n)]*\.(?:pdf|svg|eps)', source, re.IGNORECASE)
        or re.search(r'\b(?:cairo_pdf|pdf)\s*\(', source)
        or ("def save_cns_figure" in source and ".pdf" in source)
    )


def _has_raster_export(source: str) -> bool:
    return bool(
        re.search(r'(?:savefig|ggsave)\s*\([^\n)]*\.(?:png|tiff?)', source, re.IGNORECASE)
        or re.search(r'\b(?:png|tiff)\s*\(', source)
        or ("def save_cns_figure" in source and ".png" in source)
    )


# ═══════════════════════════════════════════════════════════
# Pass 0 — Anti-Pattern Scan (AP-0 through AP-7)
# ═══════════════════════════════════════════════════════════

def check_ap0_style_baseline(source: str) -> list[Finding]:
    """Verify the 3 mandatory baseline blocks are present."""
    findings = []

    # Typography baseline
    typo_required = ["font.family", "font.sans-serif", "font.size", "axes.spines.top",
                     "axes.spines.right", "axes.linewidth", "xtick.direction", "legend.frameon"]
    typo_ok = all(kw in source for kw in typo_required) and any(
        family in source for family in ("Arial", "Helvetica", "Liberation Sans")
    )
    findings.append(Finding("AP-0", typo_ok,
        "PASS" if typo_ok else "FAIL",
        "Typography baseline present" if typo_ok else
        f"Missing typography baseline. Need: {', '.join(k for k in typo_required if k not in source)}"))

    # Color baseline
    color_ok = bool(
        re.search(r'CATEGORICAL\s*=\s*\[[^]]*#2166AC[^]]*#B2182B[^]]*#1B7837', source, re.DOTALL)
        and re.search(r'DIVERGING\s*=\s*\[[^]]*#2166AC[^]]*#F7F7F7[^]]*#B2182B', source, re.DOTALL)
    )
    findings.append(Finding("AP-0", color_ok,
        "PASS" if color_ok else "FAIL",
        "Color palette baseline present" if color_ok else
        "Missing CNS color palette (CATEGORICAL/DIVERGING)"))

    # Export baseline
    export_ok = (
        _rc_setting(source, "pdf.fonttype", r'["\']?42["\']?')
        and _rc_setting(source, "svg.fonttype", r'["\']none["\']')
        and "def save_cns_figure" in source
    )
    findings.append(Finding("AP-0", export_ok,
        "PASS" if export_ok else "FAIL",
        "Export baseline (pdf.fonttype=42, svg.fonttype='none') present" if export_ok else
        "Missing export baseline — require pdf.fonttype=42, svg.fonttype='none', and save_cns_figure"))

    return findings


def check_ap1_default_palette(source: str) -> Finding:
    """Detect default matplotlib/seaborn/ggplot2 palettes."""
    defaults = [
        "cmap='tab10'", "cmap='tab20'", "cmap='jet'", "cmap='rainbow'", "cmap='hsv'",
        "plt.cm.tab10", "plt.cm.tab20", "plt.cm.jet",
        "color_palette('deep')", "color_palette('muted')", "color_palette('pastel')",
        "color_palette('bright')", "color_palette('dark')",
        "palette='deep'", "palette='muted'", "palette='Set1'", "palette='Set2'",
        "scale_color_hue()", "scale_fill_hue()",
        "scale_color_brewer(palette='Set1')", "scale_fill_brewer(palette='Set2')",
        "brewer.pal(n, 'Set1')", "brewer.pal(n, 'Paired')",
    ]
    hits = [d for d in defaults if d in source]
    ok = len(hits) == 0
    return Finding("AP-1", ok,
        "PASS" if ok else "FAIL",
        "No default palette detected" if ok else f"Default palette found: {hits}")


def check_ap2_jet_rainbow(source: str) -> Finding:
    """Detect jet/rainbow/hsv used as colormap."""
    patterns = ["cmap='jet'", "cmap='rainbow'", "cmap='hsv'",
                "cmap=\"jet\"", "cmap=\"rainbow\"", "cmap=\"hsv\""]
    hits = [p for p in patterns if p in source]
    ok = len(hits) == 0
    return Finding("AP-2", ok,
        "PASS" if ok else "FAIL",
        "No jet/rainbow colormap" if ok else f"Jet/rainbow found: {hits}")


def check_ap3_four_sided_borders(source: str) -> Finding:
    """Verify top and right spines are removed."""
    top_off = _rc_setting(source, "axes.spines.top", r'False')
    right_off = _rc_setting(source, "axes.spines.right", r'False')
    combined = bool(
        re.search(r'spines\s*\[[^]]*["\']top["\'][^]]*["\']right["\'][^]]*\]\s*\.set_visible\(False\)', source)
        or re.search(r'spines\s*\[[^]]*["\']right["\'][^]]*["\']top["\'][^]]*\]\s*\.set_visible\(False\)', source)
    )
    top_off = top_off or combined or bool(re.search(r'spines\[["\']top["\']\]\.set_visible\(False\)', source))
    right_off = right_off or combined or bool(re.search(r'spines\[["\']right["\']\]\.set_visible\(False\)', source))
    ok = top_off and right_off
    return Finding("AP-3", ok,
        "PASS" if ok else "FAIL",
        "Top/right spines removed" if ok else "Top/right spines not clearly removed — verify")


def check_ap4_legend_occlusion(source: str) -> Finding:
    """Check legend placement avoids data occlusion."""
    has_legend = bool(re.search(r'(?:\.legend|geom_legend|legend\.position)\b', source))
    if not has_legend:
        return Finding("AP-4", True, "PASS", "N/A — no legend call detected")
    has_external = bool(re.search(r'\.legend\s*\([^)]*bbox_to_anchor', source, re.DOTALL))
    has_direct = "direct label" in source.lower()
    # In R: theme(legend.position = 'right') or 'bottom' or 'none'
    has_r_external = "legend.position" in source and any(p in source for p in ["'right'", "'bottom'", "'none'"])
    ok = has_external or has_direct or has_r_external
    return Finding("AP-4", ok,
        "PASS" if ok else "WARN",
        "Legend outside plot or direct labeling" if ok else "Legend may occlude data — no bbox_to_anchor or external placement found")


def check_ap5_low_res_export(source: str) -> Finding:
    """Verify vector export + 300dpi raster."""
    ok = _has_vector_export(source)
    return Finding("AP-5", ok,
        "PASS" if ok else "FAIL",
        "Vector export present" if ok else "No vector export (PDF/SVG/EPS) — only raster found")


def check_ap6_missing_points(source: str) -> Finding:
    """For bar/box plots with small n, verify individual points shown."""
    has_points = any(kw in source for kw in
        ["stripplot", "swarmplot", "geom_point", "geom_jitter",
         "scatter", "sns.stripplot", "position_jitter"])
    has_bar = bool(re.search(r'\b(?:bar|barh|boxplot|geom_boxplot)\s*\(', source))
    if not has_bar:
        return Finding("AP-6", True, "PASS", "N/A — not a bar/box plot")
    return Finding("AP-6", has_points,
        "PASS" if has_points else "WARN",
        "Individual data points shown" if has_points else "Bar/box without individual points — add stripplot or geom_jitter")


def check_ap7_default_font(source: str) -> Finding:
    """Verify Arial/Helvetica font is explicitly set."""
    has_arial = any(f in source for f in ["Arial", "Helvetica", "Liberation Sans"])
    return Finding("AP-7", has_arial,
        "PASS" if has_arial else "FAIL",
        "Arial/Helvetica font set" if has_arial else "Default font (DejaVu Sans / R sans) — add Arial")


# ═══════════════════════════════════════════════════════════
# Pass 1 — Code-Level Compliance (CL-1 through CL-7)
# ═══════════════════════════════════════════════════════════

def _find_fontsizes(source: str) -> list[int]:
    """Parse all fontSize params from code."""
    sizes = []
    pattern = r'(?<![A-Za-z_])(?:fontsize|font\.size|labelsize|titlesize|base_size)\b["\']?\s*[=:]\s*(\d+(?:\.\d+)?)'
    for match in re.finditer(pattern, source):
        sizes.append(float(match.group(1)))
    return sizes


def check_cl1_fontsize(source: str) -> Finding:
    sizes = _find_fontsizes(source)
    if not sizes:
        return Finding("CL-1", False, "WARN", "No fontsize declarations — cannot verify the 5pt floor")
    too_small = [s for s in sizes if s < 5]
    ok = len(too_small) == 0
    return Finding("CL-1", ok,
        "PASS" if ok else "FAIL",
        f"All font sizes >= 5pt (min: {min(sizes)}pt)" if ok else f"Fonts below 5pt: {too_small}")


def check_cl2_dimensions(source: str) -> Finding:
    """Check figure dimensions match 89mm or 183mm column width."""
    # Look for size declarations in mm or inches
    mm_patterns = re.findall(r'figsize\s*=\s*\(\s*(\d+)\s*\*\s*mm_to_inch', source)
    inch_patterns = re.findall(r'figsize\s*=\s*\(\s*(\d+\.?\d*)\s*,\s*(\d+\.?\d*)\s*\)', source)
    # compose.py style: fig_width_mm / MM_PER_INCH
    compose_patterns = re.findall(r'(?:fig_width_mm|fig_w_mm)(?:\s*:\s*[A-Za-z_][\w. |]*)?\s*=\s*(\d+\.?\d*)', source)
    ratio_divs = re.findall(r'figsize\s*=\s*\(\s*(\d+\.?\d*)\s*/\s*MM_PER_INCH', source)
    ratio_slash = re.findall(r'figsize\s*=\s*\(\s*(\d+\.?\d*)\s*/\s*mm_to_inch', source)
    ratio_numeric = re.findall(r'figsize\s*=\s*\(\s*(\d+\.?\d*)\s*/\s*25\.4', source)
    # R: ggsave(width = XX, height = YY, units = "mm")
    r_mm = re.findall(r'width\s*=\s*(\d+\.?\d*)[^)]*units\s*=\s*["\']mm["\']', source, re.DOTALL)

    widths_found = []
    if mm_patterns:
        widths_found = [float(w) for w in mm_patterns]
    elif inch_patterns:
        widths_found = [float(w) * 25.4 for w, _ in inch_patterns]
    elif compose_patterns:
        widths_found = [float(w) for w in compose_patterns]
    elif ratio_divs:
        widths_found = [float(w) for w in ratio_divs]
    elif ratio_slash:
        widths_found = [float(w) for w in ratio_slash]
    elif ratio_numeric:
        widths_found = [float(w) for w in ratio_numeric]
    elif r_mm:
        widths_found = [float(w) for w in r_mm]

    if not widths_found:
        return Finding("CL-2", False, "WARN", "No explicit dimension declaration — cannot verify 89/183mm width")

    invalid = [w for w in widths_found if abs(w - 89) > 3 and abs(w - 183) > 3]
    ok = not invalid
    return Finding("CL-2", ok,
        "PASS" if ok else "FAIL",
        f"All declared widths match 89/183mm: {[round(w, 2) for w in widths_found]}" if ok
        else f"Invalid widths {invalid}; require 89±3mm or 183±3mm")


def check_cl3_dpi(source: str) -> Finding:
    """Check DPI >= 300 in savefig/ggsave calls or rcParams dict."""
    dpi_values = [int(m.group(1)) for m in re.finditer(r'dpi\s*=\s*(\d+)', source)]
    res_values = [int(m.group(1)) for m in re.finditer(r'res\s*=\s*(\d+)', source)]
    # rcParams dict form: "savefig.dpi": 300 or 'savefig.dpi': 300
    dict_dpi = [int(m.group(1)) for m in re.finditer(r'''["']savefig\.dpi["']\s*:\s*(\d+)''', source)]
    all_vals = dpi_values + res_values + dict_dpi
    if not all_vals:
        return Finding("CL-3", False, "WARN", "No explicit DPI — matplotlib defaults to 100 (insufficient for print)")
    too_low = [v for v in all_vals if v < 300]
    ok = len(too_low) == 0
    return Finding("CL-3", ok,
        "PASS" if ok else "FAIL",
        "All DPI values >= 300" if ok else f"DPI below 300: {too_low}")


def check_cl4_font_embedding(source: str) -> Finding:
    has_pdf_type = _rc_setting(source, "pdf.fonttype", r'["\']?42["\']?')
    has_svg_type = _rc_setting(source, "svg.fonttype", r'["\']none["\']')
    has_cairo_pdf = "cairo_pdf" in source
    exports_svg = ".svg" in source
    ok = (has_pdf_type or has_cairo_pdf) and (not exports_svg or has_svg_type)
    return Finding("CL-4", ok,
        "PASS" if ok else "FAIL",
        "Font embedding configured" if ok else "Require pdf.fonttype=42 or cairo_pdf; SVG export also requires svg.fonttype='none'")


def check_cl5_spine_linewidth(source: str) -> Finding:
    """Check spine linewidth is thin (0.5-0.8)."""
    lw_match = re.search(r'["\']axes\.linewidth["\']\s*(?::|\]\s*=)\s*(\d+\.?\d*)', source)
    if not lw_match:
        return Finding("CL-5", False, "WARN", "Spine linewidth not declared — cannot verify 0.5-0.8pt")
    lw = float(lw_match.group(1))
    ok = 0.4 <= lw <= 1.0
    return Finding("CL-5", ok,
        "PASS" if ok else "WARN",
        f"Spine linewidth {lw}pt in range" if ok else f"Spine linewidth {lw}pt — consider 0.5-0.6pt")


def check_cl6_tick_direction(source: str) -> Finding:
    """Verify tick direction is set outward."""
    has_out = (
        _rc_setting(source, "xtick.direction", r'["\']out["\']')
        and _rc_setting(source, "ytick.direction", r'["\']out["\']')
    ) or bool(re.search(r'tick_params\s*\([^)]*direction\s*=\s*["\']out["\']', source, re.DOTALL))
    if has_out:
        return Finding("CL-6", True, "PASS", "Ticks outward")
    return Finding("CL-6", False, "WARN", "Tick direction not explicitly set to 'out' — verify")


def check_cl7_export_completeness(source: str) -> Finding:
    has_vector = _has_vector_export(source)
    has_raster = _has_raster_export(source)
    ok = has_vector and has_raster
    return Finding("CL-7", ok,
        "PASS" if ok else "FAIL",
        "Vector + raster both exported" if ok else "Missing export — need both PDF and PNG")


CHECK_FUNCTIONS = (
    check_ap0_style_baseline,
    check_ap1_default_palette,
    check_ap2_jet_rainbow,
    check_ap3_four_sided_borders,
    check_ap4_legend_occlusion,
    check_ap5_low_res_export,
    check_ap6_missing_points,
    check_ap7_default_font,
    check_cl1_fontsize,
    check_cl2_dimensions,
    check_cl3_dpi,
    check_cl4_font_embedding,
    check_cl5_spine_linewidth,
    check_cl6_tick_direction,
    check_cl7_export_completeness,
)


def validate_source(source: str) -> list[Finding]:
    findings: list[Finding] = []
    for check in CHECK_FUNCTIONS:
        result = check(source)
        findings.extend(result if isinstance(result, list) else [result])
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="Python/R script path, or an inline source string")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--strict-warnings", action="store_true", help="Return non-zero for WARN as well as FAIL")
    args = parser.parse_args(argv)

    target = Path(args.target)
    if target.is_file():
        source = target.read_text(encoding="utf-8", errors="replace")
        source_name = str(target.resolve())
    else:
        source = args.target
        source_name = "<inline>"

    findings = validate_source(source)
    counts = {category: sum(item.category == category for item in findings) for category in ("PASS", "FAIL", "WARN")}
    report = {
        "source": source_name,
        "summary": counts,
        "passed": counts["FAIL"] == 0 and (not args.strict_warnings or counts["WARN"] == 0),
        "findings": [asdict(item) for item in findings],
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Academic Figure Skill QA: {source_name}")
        for item in findings:
            print(f"[{item.category}] {item.check_id}: {item.message}")
        print(f"Summary: {counts['PASS']} PASS, {counts['FAIL']} FAIL, {counts['WARN']} WARN")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
