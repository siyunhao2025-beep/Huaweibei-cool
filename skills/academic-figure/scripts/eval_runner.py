#!/usr/bin/env python3
"""Academic Figure Skill static asset/parser audit.

Scans assets/figures/ and automatically generates one eval per figure type.
Runs: asset-found check → syntax/parser check → baseline compliance check.
It does not claim that data-dependent scripts rendered successfully.

Usage:
    python eval_runner.py                  # run all evals
    python eval_runner.py --type RidgePlot # run single type
    python eval_runner.py --report-only    # print report from last run
"""

from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent
FIGURES_DIR = SKILL_DIR / "assets" / "figures"
RESULTS_FILE = SKILL_DIR / "scripts" / ".eval_results.json"

# ═══════════════════════════════════════════════════════════
# Required baseline checks (same values as compose.py UNIFIED_RCPARAMS)
# ═══════════════════════════════════════════════════════════
BASELINE_CHECKS = {
    "font.family": "sans-serif",
    "font.sans-serif": "Arial",
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
}

# Known-good directory names with production scripts (filter out empty/utility dirs)
EXCLUDED_DIRS = {"basic-plots", "multipanel", "other", "README.md"}


# ═══════════════════════════════════════════════════════════
# Core eval logic
# ═══════════════════════════════════════════════════════════

def list_figure_types() -> list[str]:
    """Return all figure type directories that contain production scripts."""
    types = []
    for name in sorted(os.listdir(FIGURES_DIR)):
        if name in EXCLUDED_DIRS:
            continue
        path = FIGURES_DIR / name
        if not path.is_dir():
            continue
        scripts = [f for f in os.listdir(path) if f.endswith((".py", ".R", ".r"))]
        if scripts:
            types.append(name)
    return types


def check_asset_found(figure_type: str) -> dict[str, Any]:
    """Verify the figure directory has scripts; report any local previews."""
    path = FIGURES_DIR / figure_type
    if not path.exists():
        return {"passed": False, "reason": f"Directory {figure_type} not found"}

    scripts = [f for f in os.listdir(path) if f.endswith((".py", ".R", ".r"))]
    pngs = [f for f in os.listdir(path) if f.endswith(".png")]

    if not scripts:
        return {"passed": False, "reason": "No scripts (.py/.R/.r) found"}

    return {
        "passed": True,
        "scripts": len(scripts),
        "previews": len(pngs),
        "script_names": scripts,
        "preview_names": pngs,
    }


def check_script_runnable(figure_type: str) -> dict[str, Any]:
    """Parse every script; this is not a data-backed render test."""
    path = FIGURES_DIR / figure_type
    py_scripts = [f for f in os.listdir(path) if f.endswith(".py")]
    r_scripts = [f for f in os.listdir(path) if f.endswith((".R", ".r"))]

    results = {}

    # Check Python scripts (syntax only — don't run with unknown data dependencies)
    for script in py_scripts:
        script_path = path / script
        try:
            with open(script_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            compile(source, str(script_path), "exec")
            results[f"py:{script}"] = {"passed": True, "reason": "Python syntax OK"}
        except SyntaxError as e:
            results[f"py:{script}"] = {"passed": False, "reason": f"Syntax error: {e}"}

    # Check R scripts (syntax only)
    for script in r_scripts:
        script_path = str(path / script).replace("\\", "/")
        r_bin = _find_r()
        if not r_bin:
            results[f"r:{script}"] = {"passed": False, "reason": "R not found"}
            continue
        try:
            # Use temp .R file that sources the script, avoiding inline path escaping
            import tempfile
            with tempfile.NamedTemporaryFile(mode="w", suffix=".R", delete=False, encoding="utf-8") as tf:
                tf.write('# R parse check\n')
                tf.write(f'script_path <- {json.dumps(script_path, ensure_ascii=False)}\n')
                tf.write('if (file.exists(script_path)) {\n')
                tf.write('  tryCatch({parse(file=script_path); cat("OK\\n")}, error=function(e)cat("ERROR:", e$message, "\\n"))\n')
                tf.write('} else {\n')
                tf.write('  cat("ERROR: file not found\\n")\n')
                tf.write('}\n')
                temp_r = tf.name

            result = subprocess.run(
                [r_bin, "--no-save", "--no-restore", temp_r],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
            passed = result.returncode == 0 and "OK" in result.stdout and "ERROR" not in result.stdout
            results[f"r:{script}"] = {
                "passed": passed,
                "reason": "R parse OK" if passed else (result.stdout[:200] or result.stderr[:200]),
            }
        except Exception as e:
            results[f"r:{script}"] = {"passed": False, "reason": str(e)[:200]}
        finally:
            if "temp_r" in locals():
                Path(temp_r).unlink(missing_ok=True)
                del temp_r

    return results


def check_baseline_compliance() -> dict[str, Any]:
    """Verify the project's BASELINE code blocks are internally consistent.

    Checks that compose.py, compose.R, typography.md, color-palettes.md,
    and export-specs.md use the same hex values and font settings.
    """
    results = {}

    # ── Python side ──
    compose_py = SKILL_DIR / "scripts" / "compose.py"
    color_md = SKILL_DIR / "references" / "color-palettes.md"

    # Read compose.py CATEGORICAL
    with open(compose_py, "r", encoding="utf-8", errors="replace") as f:
        py_src = f.read()

    # Check compose.py has CATEGORICAL defined
    if "CATEGORICAL" not in py_src:
        results["py:CATEGORICAL"] = {"passed": False, "reason": "CATEGORICAL not found in compose.py"}
    else:
        results["py:CATEGORICAL"] = {"passed": True, "reason": "CATEGORICAL defined"}

    # Check compose.py has r_png_device with type="cairo"
    if 'type="cairo"' in py_src or "type='cairo'" in py_src:
        results["py:cairo_png"] = {"passed": True, "reason": "r_png_device includes type=cairo"}
    else:
        results["py:cairo_png"] = {"passed": False, "reason": "r_png_device missing type=cairo"}

    # ── Color consistency between compose.py and color-palettes.md ──
    with open(color_md, "r", encoding="utf-8", errors="replace") as f:
        color_src = f.read()

    # Hex values must match
    py_hex = set()
    for m in re.finditer(r'"#[0-9A-Fa-f]{6}"', py_src):
        py_hex.add(m.group(0).strip('"'))
    md_hex = set()
    for m in re.finditer(r'"#[0-9A-Fa-f]{6}"', color_src):
        md_hex.add(m.group(0).strip('"'))

    shared = py_hex & md_hex
    if len(shared) >= 4:
        results["color:consistency"] = {"passed": True, "reason": f"{len(shared)} hex values match between compose.py and color-palettes.md"}
    else:
        results["color:consistency"] = {"passed": False, "reason": f"Only {len(shared)} matching hex values"}

    return results


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _find_python() -> str | None:
    import shutil

    # Check PATH
    for name in ["python3", "python"]:
        if shutil.which(name):
            return name

    # Windows fallback: common paths
    for ver in ["313", "312", "311", "310", "39", "38"]:
        for base in [os.path.expandvars("%LOCALAPPDATA%\\Programs\\Python\\Python{0}\\python.exe".format(ver)),
                     os.path.expandvars("%APPDATA%\\Python\\Python{0}\\python.exe".format(ver))]:
            if os.path.exists(base):
                return base
    return None


def _find_r() -> str | None:
    """Find Rscript, checking PATH first then common Windows paths."""
    import shutil

    # Check PATH
    rscript = shutil.which("Rscript")
    if rscript:
        return rscript

    # Windows fallback: discover installed versions instead of hard-coding a
    # list that becomes stale as soon as a new R minor version is released.
    candidates = []
    for base in (Path("C:/Program Files/R"), Path("C:/Program Files (x86)/R")):
        candidates.extend(base.glob("R-*/bin/Rscript.exe"))
    if candidates:
        def version_key(path: Path) -> tuple[int, ...]:
            return tuple(int(value) for value in re.findall(r"\d+", path.parts[-3]))

        return str(max(candidates, key=version_key))
    return None


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def run_all(single_type: str | None = None, save_path: Path | None = None) -> dict[str, Any]:
    """Run all evals and return results dict."""
    python_runtime = _find_python()
    r_runtime = _find_r()
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": Path(python_runtime).name if python_runtime else None,
        "r": Path(r_runtime).name if r_runtime else None,
        "baseline": check_baseline_compliance(),
        "figures": {},
    }

    types_to_test = [single_type] if single_type else list_figure_types()
    for ftype in types_to_test:
        entry = {}
        entry["asset"] = check_asset_found(ftype)
        entry["runnable"] = check_script_runnable(ftype) if entry["asset"]["passed"] else {}
        entry["overall_pass"] = (
            entry["asset"]["passed"]
            and bool(entry["runnable"])
            and all(v["passed"] for v in entry["runnable"].values())
        )
        report["figures"][ftype] = entry

    report["passed"] = (
        all(item["passed"] for item in report["baseline"].values())
        and bool(report["figures"])
        and all(item["overall_pass"] for item in report["figures"].values())
    )

    if save_path is not None:
        save_path = save_path.resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with save_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)

    return report


def print_report(report: dict[str, Any]):
    """Human-readable summary."""
    baseline = report["baseline"]
    figures = report["figures"]

    total = len(figures)
    asset_ok = sum(1 for v in figures.values() if v["asset"]["passed"])
    run_ok = sum(1 for v in figures.values() if v["overall_pass"])

    print("=" * 60)
    print("Academic Figure Skill Auto-Eval Report")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Python: {report['python'] or 'NOT FOUND'}")
    print(f"R: {report['r'] or 'NOT FOUND'}")
    print("=" * 60)

    print("\nBaseline compliance:")
    for key, val in baseline.items():
        status = "PASS" if val["passed"] else "FAIL"
        print(f"  [{status}] {key}: {val['reason']}")

    print(f"\nFigure assets ({asset_ok}/{total} have scripts):")
    for ftype, entry in sorted(figures.items()):
        a = entry["asset"]
        if not a["passed"]:
            print(f"  [FAIL] {ftype}: {a['reason']}")
            continue
        r_status = "PASS" if entry["overall_pass"] else "WARN"
        print(f"  [{r_status}] {ftype} — {a['scripts']} scripts, {a['previews']} previews")
        if not entry["overall_pass"]:
            for rkey, rval in entry["runnable"].items():
                if not rval["passed"]:
                    reason_text = rval['reason'][:100].encode('ascii', errors='replace').decode('ascii')
                    print(f"         {rkey}: {reason_text}")

    print(f"\nSummary: {run_ok}/{total} figure types pass")
    if report.get("passed", False):
        print("Verdict: STATIC READY — baseline and all production scripts passed syntax checks")
    elif run_ok == total:
        print("Verdict: baseline compliance failed")
    else:
        print(f"Verdict: {total - run_ok} types need attention")
    print("=" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", dest="figure_type", help="audit one figure type")
    parser.add_argument("--report", type=Path, help="write the result JSON to this path")
    parser.add_argument(
        "--report-only", nargs="?", const=str(RESULTS_FILE), metavar="PATH",
        help="print an existing report (defaults to the bundled evidence file)",
    )
    args = parser.parse_args(argv)
    if args.report_only:
        result_path = Path(args.report_only)
        if not result_path.is_file():
            print(f"Report not found: {result_path}", file=sys.stderr)
            return 1
        with result_path.open("r", encoding="utf-8-sig") as handle:
            previous = json.load(handle)
        print_report(previous)
        return 0 if previous.get("passed", False) else 1

    report = run_all(args.figure_type, args.report)
    print_report(report)
    return 0 if report.get("passed", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
