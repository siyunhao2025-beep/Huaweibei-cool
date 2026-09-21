# -*- coding: utf-8 -*-
"""Render every Huawei Cup modeling evidence asset with deterministic demo data."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from conftest import REPO_ROOT


FIGURES = REPO_ROOT / "skills" / "academic-figure" / "assets" / "figures"
ASSETS = {
    "ContributionWaterfall": "contribution_waterfall.py",
    "ConvergenceBand": "convergence_band.py",
    "MonteCarloRecovery": "monte_carlo_recovery.py",
    "ParameterSweep": "parameter_sweep.py",
    "PhaseProfile": "phase_profile.py",
    "ResidualDiagnostics": "residual_diagnostics.py",
    "ResourceDesign": "resource_design.py",
    "ScenarioHeatmap": "scenario_heatmap.py",
    "SensitivityTornado": "sensitivity_tornado.py",
    "TrajectoryProjection": "trajectory_projection.py",
}


@pytest.mark.parametrize(("figure_type", "script_name"), ASSETS.items())
def test_modeling_asset_renders_pdf_png_and_statistics(tmp_path, figure_type, script_name):
    script = FIGURES / figure_type / script_name
    output = tmp_path / figure_type
    process = subprocess.run(
        [sys.executable, "-X", "utf8", str(script), "--output-prefix", str(output)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    assert process.returncode == 0, f"{figure_type}\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
    result = json.loads(process.stdout.strip().splitlines()[-1])
    assert result["status"] == "PASS"
    assert result["kind"] == figure_type
    assert result["data"] == "DEMO_PREVIEW_ONLY"
    assert result["rows"] > 0
    assert result["statistics"]

    pdf = output.with_suffix(".pdf")
    png = output.with_suffix(".png")
    stats = output.with_suffix(".stats.json")
    assert pdf.read_bytes().startswith(b"%PDF-") and pdf.stat().st_size > 5_000
    assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") and png.stat().st_size > 5_000
    stored = json.loads(stats.read_text(encoding="utf-8"))
    assert stored["kind"] == figure_type
    assert stored["statistics"] == result["statistics"]
