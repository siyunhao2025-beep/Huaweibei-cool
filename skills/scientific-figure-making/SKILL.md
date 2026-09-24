---
name: scientific-figure-making
description: >-
  Covers publication-ready matplotlib figures for academic papers, slides, and
  reports—bars, trends, scatter, heatmaps, and multi-panel layouts—with this
  repository’s house style, print/vector export conventions, and parity with
  figures4papers demos. Use when the user is finalizing or creating such figures
  in matplotlib. Do not use for interactive dashboards or web viz (Plotly, Altair,
  Bokeh), exploratory-only plots without a publication target, dominant 3D or
  geographic mapping, or Illustrator/Figma-first infographic workflows.
---

# Scientific figure making

## Huaweibei-cool integration guardrails (read first)

Before opening any bundled reference or following a demo, read the repository's
[figures4papers safety profile](../academic-figure/references/figures4papers-profile.md),
[locked inventory](../academic-figure/references/figures4papers.lock.json), and
[third-party notice](../academic-figure/THIRD_PARTY_NOTICES.md). Those local
license and scientific-integrity rules override conflicting upstream-derived
recommendations in this skill.

This skill and its five bundled references remain licensed under CC BY-NC 4.0;
the repository's MIT license and the sibling Academic Figure Skill's
Apache-2.0 license do not relicense them. For commercial, enterprise, paid, or unclear
use, do not copy, execute, adapt, or redistribute this CC BY-NC
material. Route the request to the sibling Academic Figure Skill and implement
the general visualization principle independently with project-owned code.

Treat the following upstream patterns as observations, never repository
defaults:

- Magnitude bars start at zero; for narrow non-zero ranges, use a dot/interval
  plot or explicitly justified alternative instead of a truncated bar axis.
- Preserve necessary category labels; do not hide them merely because a legend
  exists.
- Do not use alpha alone for categories; add hatch, shape, line style, outline,
  or direct labels.
- Do not rely on red versus green as the only critical distinction.
- Size figures at their final 89 mm or 183 mm destination; do not inherit
  28–45 inch ultra-wide canvases.
- Keep fonts and strokes legible at final print size, and make Helvetica or TeX
  optional rather than hard runtime dependencies.

The demo links are reference-only and pinned to the audited revision recorded
in [SOURCE.md](SOURCE.md). If this skill is installed without its sibling
safety files, keep this conservative gate rather than assuming reuse is
permitted.

Open `references/` only as needed; do not preload every file. Start from the table below, then follow links inside the document you opened (and into `figure_*` code via [references/demos.md](references/demos.md)) instead of loading the full reference set up front.

## When to load this skill

- Matplotlib figures for **papers, slides, or reports** that must match **this repo’s publication look** (fonts, palette, spines, legends, export).
- Requests involving **grouped bars, trend lines, heatmaps, multi-panel grids**, or **PDF/SVG/high-DPI** output in a scientific-figure context.
- References to **figures4papers** `figure_*` projects or “same style as the repo figures.”

## When not to load

- **Plotly, Altair, Bokeh**, or other interactive / web-first plotting.
- **EDA-only** plots where seaborn or pandas is enough until there is a publication target.
- Primary workflow is **3D, GIS**, or **non-matplotlib** tooling.
- **Illustrator / Figma–first** layout or infographic (not matplotlib data plots).

## Related files

| File | Open when |
|------|-----------|
| [references/tutorials.md](references/tutorials.md) | End-to-end walkthroughs (bar, trends, heatmap) |
| [references/api.md](references/api.md) | Function signatures, `PALETTE`, validation rules |
| [references/common-patterns.md](references/common-patterns.md) | Layout patterns, legend panel, print-safe bars |
| [references/design-theory.md](references/design-theory.md) | Typography, export policy, palette rationale |
| [references/demos.md](references/demos.md) | Canonical `figure_*` demo links in figures4papers |
