# figures4papers: audited technique profile

This profile is an independently written, safety-adjusted design reference for
Academic Figure Skill. It covers every file in the locked upstream tree, but
it is not a substitute for the upstream license and does not grant permission
to copy upstream code, prose, figures, or paper data.

## Source, scope, and use gate

- Source: `ChenLiu-1996/figures4papers`
- Locked commit: `3c181f85e82c6f24948fcaaf3be6696102b41d8d`
- License: CC BY-NC 4.0 (attribution, link, change notice, noncommercial use)
- Audited tree: 95 entries / 76 files / 33,947,895 bytes
- File mix: 25 Python, 39 PNG, 3 PDF, 7 Markdown, plus license and `.gitignore`
- Full per-file disposition: `references/figures4papers.lock.json`
- Existing in-tree third-party mapping: `THIRD_PARTY_NOTICES.md`

Before using an asset, classify the intended use:

1. **Commercial, enterprise, paid consulting, or unclear:** do not copy or
   execute the CC BY-NC asset as a production template. Reimplement the
   general visual principle from first principles using project-owned code,
   synthetic data, and the safeguards below.
2. **Clearly noncommercial and attribution can travel with the output:** the
   listed in-tree files may be used under CC BY-NC 4.0. Preserve the credit,
   source URL, license link, locked revision, and modification notice.
3. **Publication image, paper data, or composite raster:** reference-only by
   default. Do not redistribute without separate rights verification.

This gate overrides any generic `COPY-FIRST`, “copy verbatim,” or parameter
inheritance instruction elsewhere in this skill.

## Technique ledger

The decision terms are:

- **adopt** — use the general method in new project-owned code;
- **adapt** — retain the idea only after the stated scientific/operational fix;
- **reject** — do not make it a default;
- **reference-only** — recognize the pattern, but do not redistribute the source.

| ID | Pattern learned from the audited corpus | Decision | Safe production rule |
|---|---|---|---|
| F4P-BAR-01 | Single-metric method comparison with direct values | adapt | Bar charts start at zero unless the break is explicit and scientifically justified; show points or intervals when repetitions exist. |
| F4P-BAR-02 | Multi-panel, multi-metric comparisons | adapt | Keep method identity stable, but size panels to final physical width rather than a 28–96 inch canvas. |
| F4P-BAR-03 | Horizontal ablation bars with component-code labels | adapt | Decode components in plain language; use hatch/marker/outline as well as color; disclose the reference model. |
| F4P-BAR-04 | Grouped bars with manual inter-group gaps | adopt | Compute group centers explicitly and preserve readable group labels; include units and sample count. |
| F4P-BAR-05 | 100% stacked composition with cumulative bottoms | adopt | Verify every stack sums to the declared denominator and state whether percentages are row-, column-, or global-normalized. |
| F4P-BAR-06 | Color for method plus hatch for state | adopt | Retain redundant channels and separate method/state legends. |
| F4P-ERR-01 | `xerr`/`yerr`, caps, and value labels | adapt | Caption must name SD, SE, CI, quantile, or range; never draw an unlabeled generic “error.” |
| F4P-ERR-02 | Baseline line, delta arrow, and loss label | adopt | Compute delta from the same stored values used to draw marks; include directionality and uncertainty where applicable. |
| F4P-LINE-01 | Hyperparameter and training-step trajectories | adopt | Use fixed, interpretable ticks; indicate optimum/reference lines without hiding non-optimal regions. |
| F4P-LINE-02 | Segmented opacity gradient along a trajectory | adapt | Opacity is secondary only; also encode progression with position, marker, annotation, or line style. |
| F4P-LINE-03 | Two metrics on `twinx` | adapt | Prefer aligned small multiples. If dual axes are necessary, bind each axis to a labeled color/line and warn against slope comparison. |
| F4P-TIME-01 | Cumulative area, hatching, and event annotations | adopt | Parse dates strictly, deduplicate keys, expose missing months, and keep event labels collision-free. |
| F4P-HEAT-01 | Annotated count heatmap with row/column totals | adopt | Totals must be recomputed from the plotted matrix; use a single declared scale and contrast-aware text. |
| F4P-HEAT-02 | One normalization/colormap per metric column | adapt | Use only when units truly differ; give each column an explicit scale/legend and state that color depth is not comparable across columns. |
| F4P-HEAT-03 | Summary row separated from the value matrix | adapt | Label whether the row is an absolute value, signed delta, percent change, or rank; do not reuse a misleading matrix color scale. |
| F4P-RADAR-01 | Per-benchmark spoke normalization and custom grids | adapt | Show original-scale ticks, document bounds and direction, avoid area-based claims, and prefer aligned dot/slope plots when precision matters. |
| F4P-MAN-01 | Gaussian transition matrix and Swiss-roll graph | adapt | Fix the random seed, vectorize or sparsify expensive pairwise work, and label the rendering as an embedding/illustration rather than proof of geometry. |
| F4P-CONCEPT-01 | Gaussian distributions, shaded gaps, arrows, math labels | adopt | Mark simulated/conceptual data and never present it as measured evidence. |
| F4P-CONCEPT-02 | KDE contours, spline centerlines, paths, and star markers | adapt | Treat density/manifold pictures as conceptual unless computed from traceable data; keep generated samples and seeds. |
| F4P-GEO-01 | 2D Lambert-like shading to suggest a 3D sphere | adapt | Explicitly label it as a schematic; do not imply a numerical 3D reconstruction. |
| F4P-GEO-02 | Lift to hemisphere plus SLERP great-circle path | adopt | Clamp dot products, handle coincident/antipodal cases, and state the coordinate/projection convention. |
| F4P-GEO-03 | Sphere/ellipsoid overlays and correspondence arrows | adapt | Preserve equal aspect and disclose when shape is an illustrative transform rather than fitted geometry. |
| F4P-3D-01 | Custom 3D arrows, scatter/quiver, hidden panes | adapt | Always pair with an inspectable 2D projection or quantitative panel; use equal aspect and a documented camera. |
| F4P-3D-02 | Multi-peak surfaces, custom face colors, and masked holes | adapt | Keep the source grid and mask; add colorbar/units when color encodes magnitude; distinguish missing from zero. |
| F4P-LAYOUT-01 | Dedicated legend-only subplot | adopt | Use when it increases data area and keeps the reading order obvious; otherwise use a shared figure legend. |
| F4P-LAYOUT-02 | Split legends for method and state | adopt | Use semantically distinct title labels and identical order across panels. |
| F4P-LAYOUT-03 | Asymmetric width ratios and manual panel movement | adapt | Derive ratios from information density, then run overlap/crop checks at final size. |
| F4P-LAYOUT-04 | Ultra-wide one-row narratives | reject | Replace with journal-width grids, wrapped rows, or a main/supplement split. |
| F4P-TYPE-01 | Large Helvetica-centric typography | adapt | Detect fonts and use `Arial -> Helvetica -> Noto Sans/DejaVu Sans -> sans-serif`; verify glyph coverage and final-size readability. |
| F4P-TYPE-02 | Runtime `text.usetex=True` | adapt | Make TeX opt-in and fall back to MathText; never require an undeclared system TeX install. |
| F4P-ANNOT-01 | Contrast-aware black/white cell or bar text | adopt | Calculate luminance/contrast from rendered face color; test light and dark backgrounds. |
| F4P-ANNOT-02 | Gold text with outline on busy fills | adapt | Reserve outlined accents for sparse callouts; prefer a quiet label background for dense charts. |
| F4P-EXPORT-01 | Predominantly 300 DPI PNG, selected 600 DPI | adapt | Deliver PDF/SVG for line art plus a 300 DPI preview; use 600 DPI only when the journal/raster detail requires it. |
| F4P-EXPORT-02 | `tight_layout` and occasional tight bounding box | adapt | Prefer constrained layout for complex figures, then render and check crop, overlap, legend, and glyph coverage. |
| F4P-REPRO-01 | Relative output paths and script-local data imports | reject | Resolve paths from an explicit work/output directory; never depend on the caller's current directory. |
| F4P-REPRO-02 | Hard-coded paper arrays and labels | reference-only | Production figures consume user data or declared synthetic fixtures; copied paper results are never defaults. |
| F4P-ASSET-01 | Composite pipeline/result rasters with panel letters and shared color semantics | reference-only | Learn hierarchy and alignment only; editable layers, icons, fonts, molecular renderers, and third-party rights are unknown. |

## Figure-family playbook

### Bars and ablations

Use grouped, horizontal, stacked, or 100% stacked bars only when discrete
comparisons are the question. Keep a zero baseline for magnitude bars. Pair
method color with hatch, outline, marker, or direct label; place exact values
only when they aid comparison. For repeated experiments, show raw points or a
distribution whenever panel density permits. A baseline/delta annotation is
useful when the delta is the scientific claim, but it must be computed from
the same table and inherit its uncertainty.

### Lines, sweeps, and timelines

Use two to four salient trajectories per panel. A gradient segment may express
progress but cannot be the only key. A reference line needs a named meaning.
For cumulative timelines, preserve the original dates, make missing periods
visible, and anchor event callouts to actual time/value coordinates. Prefer
small multiples over dual axes; when `twinx` is unavoidable, prevent readers
from comparing slopes across different scales.

### Heatmaps

Use a common normalization when cells should be compared directly. Per-column
normalization is acceptable for heterogeneous metrics only with per-column
scale disclosure. Diverging data need a meaningful center, usually zero or a
declared baseline. Render missing values distinctly. Annotation color follows
measured contrast, not a hard-coded threshold. Summary rows are visually and
semantically separated from raw matrices.

### Radar and polar views

Radar charts are overview devices, not precise quantitative evidence. Record
each spoke's original unit, favorable direction, min/max, and clipping rule.
Do not argue from polygon area after per-spoke normalization. For reviewer-
critical comparisons, add a table, dot plot, or slope chart with original
values.

### Manifold, probability, geometry, and 3D

Distinguish three statuses in the caption: measured result, simulation, or
conceptual schematic. KDE, Swiss roll, diffusion graph, shaded sphere, SLERP,
custom 3D arrows, and masked surfaces are valid explanatory tools only when
their data, seed, transform, camera, and limits are traceable. A 3D panel must
have an inspectable 2D quantitative companion unless the geometry itself is
the result.

## Layout system

- Start from the final destination: 89 mm single-column or 183 mm double-column.
- Use a regular grid for panels of equal evidential weight; use an asymmetric
  main/support layout when one panel carries the central claim.
- A legend-only cell is allowed when it eliminates overlay and repeated
  legends. Delete placeholder marks after extracting handles.
- Keep panel letters, title baselines, axis-label offsets, and gutters aligned.
- Wrap long one-row narratives into two rows instead of expanding the canvas.
- After layout, render at final size and check collision, crop, whitespace,
  reading order, and panel-to-caption correspondence.

## Typography

Use a fallback stack rather than a single assumed font. Verify Chinese and
mathematical glyphs with a real canvas draw. Set type relative to final
physical dimensions, not the oversized working canvas. Keep a clear hierarchy
among panel letters, axis labels, ticks, legends, and callouts. MathText is the
portable default; TeX is optional and must be detected before use.

## Color and redundant encoding

The audited corpus uses a recognizable blue/green/red family. Treat the values
below as provenance evidence, not as an automatically relicensed house style:

| Role observed upstream | Values observed | Safe use in this skill |
|---|---|---|
| Emphasis / proposed method | `#0F4D92`, `#3775BA` | May inspire a project-owned blue emphasis role; test contrast. |
| Positive progression | `#DDF3DE`, `#AADCA9`, `#8BCF8B` | Do not rely on green alone; pair with shape/label. |
| Comparison / negative | `#F6CFCB`, `#E9A6A1`, `#B64342` | Avoid red-vs-green as the sole opposition. |
| Neutral/reference | `#CFCECE` and gray ramps | Keep sufficient foreground/background contrast. |
| Sparse highlight | `#FFD700` | Reserve for one or two callouts; outline only if required. |
| Secondary concepts | `#42949E`, `#9A4D8E` | Check color-vision simulation and grayscale. |
| Sequential/diverging maps | `viridis`, gray, `Reds`, `Blues_r`, `coolwarm` | Prefer perceptually uniform maps; choose a meaningful center for divergence. |

Observed project-specific sets include warm red ramps, pastel method families,
green surface ramps, and blue/red timeline areas. Do not copy the complete set
as a default theme. Select a colorblind-safe palette such as Okabe-Ito/Tol or
a perceptually uniform map, then add redundant encoding: hatch (`/`, `\\`,
`x`, `|`, `-`), solid/dashed/dotted line, circle/star marker, outline, and
direct label. Alpha is for uncertainty, density, or layering—not category
identity by itself.

## Annotation rules

- Add `up/down` direction to metric labels only when direction is defined.
- Recalculate every printed number from the plotted data source.
- Use contrast-aware text and quiet boxes for dense backgrounds.
- Keep arrows anchored in data coordinates or deliberately transformed axes.
- Separate real observations from explanation-only handles and glyphs.
- Captions state unit, denominator, sample size, uncertainty type, transform,
  normalization, and whether the panel is measured, simulated, or conceptual.

## Export and reproducibility contract

1. Resolve input/output paths explicitly and create the output directory.
2. Record data hash, script version, random seed, dependency versions, font
   fallback, physical size, DPI, and output formats.
3. Default to vector PDF/SVG for marks/text and a 300 DPI PNG preview; rasterize
   only dense image-like layers.
4. Preserve editable text where the format supports it and check PDF/SVG font
   embedding or substitution.
5. Use a headless backend for automation, close figures, and reject accidental
   import-time rendering.
6. Warn before any canvas that would exceed a configured pixel/memory ceiling.
7. Render with synthetic data for smoke tests; never use copied paper values as
   an implicit fixture.

## Known upstream defects converted into guards

- Detect duplicate mapping keys and malformed dates before timeline rendering.
- Assert that every method has exactly one style entry; no color-list mismatch.
- Assert that each series is drawn once; catch duplicate plotting calls.
- Put rendering behind `main()`; importing a module must not write files.
- Require explicit DPI and at least one vector master.
- Seed stochastic demonstrations and avoid quadratic graph drawing when sparse
  neighbors suffice.
- Detect unavailable Helvetica/TeX and fall back instead of failing at render.

## Huawei Cup adapter

Translate the general techniques into competition evidence, never into copied
benchmark stories:

| Competition question | Preferred evidence family | Required safeguard |
|---|---|---|
| Is the proposed method better? | point/interval or grouped comparison | Same metric/scale, repetitions visible, uncertainty named |
| Which component matters? | ablation with baseline/delta | Zero baseline for bars, component meaning, paired runs where possible |
| How sensitive is the conclusion? | parameter sweep/heatmap/tornado | Feasible region, direction, robustness neighborhood |
| Does optimization converge? | multi-seed line and uncertainty band | Seed count, stop criterion, constraint violations |
| Is the model calibrated/valid? | residual, recovery, coverage, confusion/ROC | Held-out protocol and denominators |
| How does a process evolve? | trace/timeline/phase profile | Real time/phase units and event provenance |
| What is the mechanism? | schematic plus quantitative support | Explicit “schematic” label and no fabricated measurements |
| What is the trade-off? | Pareto/dot/slope plot | Original units; radar only as secondary overview |

The resulting figure still follows the repository contract: evidence first,
then cause/mechanism, implication, and boundary. A visually polished panel
cannot compensate for missing data lineage or an unsupported causal claim.
