# QA Protocol

This is an **LLM-executable** quality assurance protocol. After generating figure code, the LLM executes this protocol automatically as Step 5 of the Hub workflow. Each check specifies what to look for in the generated code and how to verify it—no external scripts required.

## Automated Validation

Run automated checks on any generated script:
```bash
python academic-figure-skill/scripts/qa_validator.py <script.py>
```
This validates AP-0 through CL-7 without human review. See `academic-figure-skill/scripts/qa_validator.py` for the full check suite.

## Protocol Structure

The protocol runs in four passes. Pass 0 catches common anti-patterns. Pass 1 verifies code-level compliance. Pass 2 checks visual logic and data integrity. Pass 3 verifies the rendered output. Each failed check includes the fix action.

**Stop condition:** If Pass 0 or Pass 1 finds >2 failures, fix them and re-run the pass before proceeding. A pass with no failures and at most 2 minor warnings can proceed with those warnings recorded in the report.

---

## Pass 0: Anti-Pattern Scan (Fast, High-Impact)

Run these checks first. They catch the issues reviewers flag most often and take seconds to verify.

### AP-0: Style Baseline Injection

**How to check:** Verify the generated code begins with the three mandatory baseline blocks from the reference files. Search for the exact code patterns in order:

1. Typography baseline: must contain ALL of: `font.family`, `font.sans-serif`, `font.size: 8`, `axes.spines.top: False`, `axes.spines.right: False`, `axes.linewidth: 0.6`, `xtick.direction: 'out'`, `legend.frameon: False`
2. Color palette baseline must contain: `CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]` AND `DIVERGING = ["#2166AC", "#F7F7F7", "#B2182B"]`
3. Export baseline—must contain: `pdf.fonttype: 42` AND `svg.fonttype: 'none'` AND a function named `save_cns_figure`

**Pass condition:** All three baseline blocks present, with exact values. No modification, no omission, no "similar version."

**Fix if FAIL:** Copy the verbatim blocks from `references/typography.md`, `references/color-palettes.md`, and `references/export-specs.md`. Insert at script top before any panel code. Do not edit the values.

### AP-1: Default Color Palette

**How to check:** Scan the generated code for these patterns. Any match = FAIL.

| Pattern | What it means |
|---------|---------------|
| `cmap='tab10'`, `cmap='tab20'`, `cmap='jet'`, `cmap='rainbow'`, `cmap='hsv'` | matplotlib default colormap |
| `plt.cm.tab10`, `plt.cm.tab20`, `plt.cm.jet` | matplotlib built-in colormap reference |
| `sns.color_palette('deep')`, `sns.set_palette('muted')`, `sns.color_palette()` | seaborn default palette (deep/muted/pastel/bright/dark/colorblind) |
| `palette='deep'`, `palette='muted'`, `palette='Set1'`, `palette='Set2'` | seaborn/ggplot2 default palette name |
| `scale_color_hue()`, `scale_fill_hue()` | ggplot2 default hue scale |
| `scale_color_brewer(palette='Set1')`, `scale_fill_brewer(palette='Set2')` | ggplot2 Brewer qualitative scale |
| `brewer.pal(n, 'Set1')`, `brewer.pal(n, 'Paired')` | RColorBrewer qualitative palette |

**Fix if FAIL:** Replace with custom hex colors. Load `references/color-palettes.md` and choose a semantic palette. Never just swap to viridis—choose colors that serve the figure's scientific message.

**Pass condition:** None of the above patterns appear in the code. Custom hex colors (`#XXXXXX`) are used instead.

### AP-2: Jet / Rainbow Colormap

**How to check:** Search for `jet`, `rainbow`, `hsv` used as colormap names.

**Fix if FAIL:** Replace with a perceptually uniform sequential colormap. For diverging data, use the Academic Figure Skill standard `#2166AC - #F7F7F7 - #B2182B`. For sequential, use viridis, cividis, or a custom blue sequential.

**Pass condition:** No jet/rainbow/hsv colormap in continuous data contexts.

### AP-3: Four-Sided Borders

**How to check:** Verify these are present in the code (they disable top/right spines):

- **Python:** `axes.spines.top: False` AND `axes.spines.right: False` (in rcParams or per-axis)
- **R ggplot2:** `theme(panel.grid = element_blank())` or `theme_bw()` + spine removal, or a clean theme
- **R base:** Explicit `bty='l'` or spine removal

**Fix if FAIL:** Add spine removal. For matplotlib: `ax.spines[['top','right']].set_visible(False)`. For R: `theme(panel.grid = element_blank())`.

**Pass condition:** Top and right spines removed; no default grey grid background.

### AP-4: Legend Occlusion

**How to check:** Look for `ax.legend()` or `plt.legend()` called without `bbox_to_anchor` OR `loc` outside the plot area, where the legend would default to inside the plot. Also check R: `theme(legend.position = c(...))` with coordinates inside the plot area.

**Fix if FAIL:** Move legend outside: `ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', frameon=False)` in Python; `theme(legend.position = 'right')` or `'bottom'` in R. Alternatively, use direct labeling (annotate data points/lines directly).

**Pass condition:** Legend outside plot area, or justified internal placement with no data occlusion, or direct labeling used instead.

### AP-5: Low-Resolution Export Only

**How to check:** Does the code include a vector export (`savefig(..., '*.pdf')`, `savefig(..., '*.svg')`, `ggsave('*.pdf')`, `ggsave('*.svg')`, `cairo_pdf()`, `pdf()`)? If only PNG/JPG export is present, FAIL.

**Fix if FAIL:** Add vector export. Python: `fig.savefig('figure.pdf', bbox_inches='tight', dpi=300)`. R: `ggsave('figure.pdf', device=cairo_pdf)`.

**Pass condition:** At least one vector format export (PDF/SVG/EPS) present in the code.

### AP-6: Missing Individual Data Points (Small n)

**How to check:** If the figure is a bar chart or boxplot, and the sample size appears small (n < 10 per group from the data or from context), verify individual data points are shown. Check for `stripplot`, `swarmplot`, `geom_point`, `geom_jitter`, or `scatter` overlay.

**Fix if FAIL:** Overlay individual points. Python: `sns.stripplot()` or `ax.scatter()` with jitter. R: `geom_point(position = position_jitter(width = 0.1))`.

**Pass condition:** Individual data points visible for bar/box plots with small n. If n is clearly large (>30 per group), this check is N/A.

### AP-7: Default Font

**How to check:** Verify the font family is explicitly set to Arial, Helvetica, or Liberation Sans. Check for `font.family` or `font.sans-serif` in Python rcParams; `base_family` or `element_text(family=...)` in R.

**Fix if FAIL:** Python: add `font.sans-serif: ['Arial', 'Helvetica', 'Liberation Sans']` to rcParams. R: add `base_family = 'Arial'` to theme or use `showtext` package.

**Pass condition:** Font family explicitly set to Arial/Helvetica/Liberation Sans, not left at system default (DejaVu Sans, R default sans).

---

## Pass 1: Code-Level Compliance

Each check includes: **what to scan for**, **the pass condition**, and **the fix if failed**.

### CL-1: Font Size Floor

**Scan for:** All fontsize declarations in the code.
- Python: `font.size`, `fontsize=`, `labelsize`, `titlesize` parameters
- R: `base_size`, `element_text(size=)`, `gpar(fontsize=)`

**Pass condition:** No fontsize value < 5 pt. The base/default fontsize is at least 5 pt (typically 6–7 pt for journal figures).

**Fix if FAIL:** Raise the sub-5 pt value to at least 5 pt. For axis tick labels on dense figures, 5 pt is acceptable. For anything else, use 6–7 pt minimum.

### CL-2: Figure Dimensions

**Scan for:** Figure size declarations.
- Python: `figsize=(W, H)`, `W * mm_to_inch`, `W / 25.4`
- R: `width = W, height = H` with `units = 'mm'` or `'in'`

**Pass condition:** Width is within ±3 mm of 89 mm (single-column) or 183 mm (double-column). Height is at most 247 mm.

**Fix if FAIL:** Adjust dimensions to match the target column width. Recalculate: `figsize=(89/25.4, height/25.4)` for single-column.

### CL-3: Export DPI

**Scan for:** `dpi=` in savefig/ggsave, `res=` in R png/tiff devices.

**Pass condition:** DPI is at least 300 for raster exports. Vector exports (PDF/SVG) don't need DPI but having `dpi=300` is harmless.

**Fix if FAIL:** Set `dpi=300` in all raster save calls. Default matplotlib DPI is 100—insufficient for print.

### CL-4: Font Embedding

**Scan for:** `pdf.fonttype`, `svg.fonttype` in Python rcParams. `cairo_pdf` or `showtext` usage in R.

**Pass condition:** `pdf.fonttype: 42` present (Python). `cairo_pdf()` or `showtext` used (R). `svg.fonttype: 'none'` present (Python, if SVG export used).

**Fix if FAIL:** Add `"pdf.fonttype": 42` and `"svg.fonttype": "none"` to rcParams (Python). Use `cairo_pdf()` device (R).

### CL-5: Spine Linewidth

**Scan for:** `axes.linewidth` in Python rcParams. `axis.line` or `panel.border` theme elements in R.

**Pass condition:** Spine linewidth is 0.5-0.8pt. Data elements (lines, points) use thicker strokes.

**Fix if FAIL:** Set `axes.linewidth: 0.6` in rcParams (Python) or adjust `axis.line` in theme (R). The default 1.0-1.5pt spine is too heavy for journal figures.

### CL-6: Tick Direction

**Scan for:** `xtick.direction`, `ytick.direction` in Python rcParams. `axis.ticks` theme in R.

**Pass condition:** Ticks directed outward (`'out'`), not inward. Inward ticks can overlap data at plot boundaries.

**Fix if FAIL:** Set `xtick.direction: 'out'` and `ytick.direction: 'out'` in rcParams.

### CL-7: Export Completeness

**Scan for:** Save/export calls in the code.

**Pass condition:** At least one vector save (`*.pdf`, `*.svg`, or `*.eps`) AND at least one raster preview (`*.png` or `*.tiff` at ≥300 dpi). Both must exist in the delivered code.

**Fix if FAIL:** Add the missing export. Always deliver both formats.

---

## Pass 2: Visual Logic & Data Integrity

These checks require reasoning about what the code produces, not just pattern matching. The LLM reads the code, imagines the output, and verifies visual logic.

### VI-1: Core Conclusion Visibility

**Question:** If a reviewer looks at this figure for 3 seconds, do they see the core conclusion from Step 0?

**How to check:** Look at the code's visual hierarchy—which element has the strongest visual weight (largest, most saturated color, most prominent position)? Does that element carry the conclusion? Or is a secondary element visually dominant?

**Pass condition:** The element carrying the core conclusion is visually dominant. If the hero element and the conclusion don't align, FAIL.

**Fix if FAIL:** Adjust visual weights—increase hero element size/saturation, reduce competing elements, reposition. If the conclusion can't be made visually dominant, the figure needs restructuring.

### VI-2: Color Accessibility

**Question:** Is the figure interpretable in greyscale? Are red and green the only distinguishing colors for any critical comparison?

**How to check:**
1. Scan for `#FF0000`/`red` AND `#00FF00`/`green` used as the only two category colors
2. Verify at least one non-color differentiator exists for critical comparisons (shape, line style, direct label, faceting)

**Pass condition:** No red-green only pair for critical comparisons. At least one of: additional differentiator, colorblind-safe palette, or direct labels.

**Fix if FAIL:** Add shape/linetype differentiation, or swap the red-green pair for blue-orange or blue-purple. For continuous data, ensure the colormap is perceptually uniform.

### VI-3: Data-Ink Ratio

**Question:** Is any visual element present that doesn't carry information?

**How to check:** Look for: gridlines (especially major AND minor), decorative borders, redundant legend entries, unnecessary background fills, chartjunk (3D effects on 2D data, gratuitous gradients, drop shadows).

**Pass condition:** All visual elements serve a data-communication purpose. Gridlines absent or minimal (very light, major only). No decorative elements.

**Fix if FAIL:** Remove the non-data element. If gridlines are needed for reader guidance, use `color='#E0E0E0', linewidth=0.3, alpha=0.3`.

### VI-4: Axis Range Correctness

**Question:** Does the y-axis range serve the data, or does it mislead?

**How to check:**
1. Does the y-axis start at 0 for bar charts? (Required—bars encode value by length from baseline.)
2. For non-bar charts, is the axis range close to the data range? (If all values are 80-95, the axis should be ~75-100, not 0-100)
3. For log scales, is the scale explicitly noted in the axis label?

**Pass condition:** Bar charts start at 0. Non-bar axes are tight to data. Log scales labeled.

**Fix if FAIL:** Adjust axis limits. For bars: `ax.set_ylim(0, ...)`. For non-bars: `ax.set_ylim(data_min*0.9, data_max*1.1)`.

### VI-5: Statistical Annotation Completeness

**Question:** Are statistical claims supported by visible evidence?

**How to check:** If the code includes significance brackets, p-values, or statistical annotations, verify:
1. The test used is named or inferable from context
2. Error bars are defined (SD, SEM, or CI—which one?)
3. n is stated or computable from the data
4. Asterisk thresholds are defined if asterisks used

**Pass condition:** Statistical annotations are complete and self-contained. A reader doesn't need the caption to understand what the stats mean.

**Fix if FAIL:** Add the missing information. Prefer exact p-values over asterisks. Define error bar type in a code comment or on the figure.

### VI-6: Panel Label Consistency (Multi-Panel Only)

**Question:** Are panel labels consistent in position, font, and style?

**How to check:** Verify all panel label calls use the same coordinate system, same fontsize, same fontweight, and same position offset. Check for mixed placement strategies (top-left on panel a, bottom-right on panel d).

**Pass condition:** All labels use identical styling and positioning. No label is missing.

**Fix if FAIL:** Unify all label calls to the same pattern. Standard: `ax.text(-0.12, 1.02, label, transform=ax.transAxes, fontsize=8.5, fontweight='bold')`.

### VI-7: Revision Case Cross-Reference

**Question:** Does this figure type + journal combination match any known peer-review rejection patterns?

**How to check:** Load `references/revision-cases.md`. Scan the cases for matches against:
1. The user's figure type (e.g., heatmap, volcano, bar chart)
2. The user's target journal (if specified)
3. Common failure patterns for that figure type (e.g., "heatmap → default red-blue colormap", "volcano → missing threshold lines", "bar chart → no individual data points when n < 10")

**Pass condition:** For each matching case, the generated code must NOT contain the failure pattern described. If a case warns about default colormaps and the code uses `cmap='jet'`, FAIL.

**Fix if FAIL:** Apply the fix described in the matching revision case. Each case includes the exact reviewer comment, the fix action, and the lesson learned.

**Example matches:**
- Heatmap + Nature Genetics → check Case 1 (default red-blue colormap)
- Bar/box + n < 10 → check Case 2 (missing individual data points)
- Volcano → check Case 3 (missing significance thresholds)
- Multi-panel → check Case 4 (inconsistent styling across panels)
- Schematic/model → check Case 10 (inconsistent visual language)
- Correlation heatmap → check Case 8 (missing mask fill)
- Phylogenetic tree → check Case 9 (illegible tip labels)

---

## Pass 3: Visual Verification (Render + Inspect)

Passes 0-2 verify the **code**. Pass 3 verifies the **output**. These are problems invisible in code but obvious in the rendered figure.

### VV-1: Data Occlusion

**Question:** Does any visual element cover or overlap data points, labels, or other critical information?

**How to check:** Inspect the rendered PNG. Look for:

| Issue | Where to Look |
|-------|--------------|
| Legend overlapping data | Legend bounding box vs scatter/bar coordinates |
| Gene/point labels overlapping each other | Dense regions near label annotations |
| Colorbar crowding plot area | Right edge of heatmap/UMAP |
| Error bars crossing axis labels | Bottom/top margins |
| Panel labels covering data | Top-left corner of each panel |

**Fix if FAIL:**
- Legend occlusion → use `bbox_to_anchor=(1.02, 1)` to move outside, or adjust `loc` to an empty corner
- Label overlap → reduce fontsize by 1 pt, increase `xytext` offset, or label fewer items; use `adjustText` (Python) or `ggrepel` (R) for automatic label avoidance
- Colorbar crowding → increase `pad`, reduce `shrink`, or move the colorbar horizontally below the plot
- Error-bar collision → increase the y-axis upper limit by 10–15%
- Panel-label occlusion → move the label offset from (-0.08, 1.02) to (-0.15, 1.04)

**Pass condition:** No data occlusion visible. All labels, legends, and annotations are clearly separated from data elements.

### VV-2: Layout Regularity

**Question:** Do panels align properly? Are margins consistent? Is the figure balanced?

**How to check:** Inspect the rendered PNG. Look for:
- Uneven panel widths/heights in a grid
- Misaligned panel edges
- One panel much smaller/larger than peers (unless intentional hero panel)
- Text cut off at figure boundaries
- Excessive or inconsistent whitespace between panels
- Colorbar extending beyond panel boundary

**Fix if FAIL:**
- Uneven panels → enforce explicit `width_ratios` and `height_ratios` in gridspec; use `sharex=True, sharey=True` for same-axis panels
- Text cut off → increase figure margins: `gs.update(left=0.12, bottom=0.12)` or use `bbox_inches='tight'`
- Uneven spacing → use consistent `wspace` and `hspace` values across the entire gridspec
- One panel dominating → check whether it is the intended hero panel; if not, adjust `height_ratios` or `width_ratios`

**Pass condition:** Panels are aligned, margins are consistent, no text is cut off, and the layout looks intentional.

### VV-3: Text Legibility

**Question:** Is all text actually readable at the rendered size?

**How to check:** Inspect the rendered PNG. This is the ground truth—code-level fontsize checks in CL-1 verify the setting, but only visual inspection verifies the result. Check:
- Axis tick labels—especially long strings or rotated labels
- Gene/protein names—italic text at small sizes can blur
- Legend text—often the smallest text on the figure
- Colorbar tick labels—can be crushed if the colorbar is narrow
- Panel labels—should be immediately visible, not lost in margin clutter

**Fix if FAIL:**
- Tick labels too small → raise from 5 pt to 6 pt, or rotate 45° instead of 90°
- Gene labels illegible → increase from 4 pt to 5 pt, or switch from italic to regular (regular text is more legible at small sizes than italic)
- Legend unreadable → increase fontsize by 1 pt, reduce legend content, or move to a larger panel
- Colorbar labels crushed → increase colorbar width (`aspect=10` instead of `aspect=15`)

**Pass condition:** The reader can read every text element without squinting, at the intended print size.

### VV-4: Color Rendering

**Question:** Do colors render as intended? Are adjacent colors distinguishable?

**How to check:** Inspect the rendered PNG. Verify:
- Adjacent categorical colors are visually distinct (not two shades of the same hue)
- Gradient/sequential colormaps show visible progression (not all looking like the same color)
- Threshold lines are visible against the background data density
- Grey NS points in volcano/UMAP don't overpower colored signal points
- White or very light elements are visible against white background

**Fix if FAIL:**
- Adjacent colors too similar → increase hue separation; swap one for a color farther away on the color wheel
- Gradient invisible → adjust `vmin`/`vmax` to the declared scientific scale, or switch to a higher-contrast colormap without clipping observations
- Threshold line lost → darken the line to `#444444`, increase linewidth to 0.8 pt, or add a subtle annotation
- NS points overpower signal → reduce NS-point alpha from 0.4 to 0.25, or plot NS points first (lower z-order)
- Light elements invisible → add a very thin dark edge (`edgecolors='#CCCCCC', linewidth=0.1`)

**Pass condition:** All color distinctions are clearly visible. Nothing blends into the background or another category.

### VV-5: Data Integrity and Faithful Rendering

**Question:** Does the figure faithfully render the supplied or computed data, including valid null or weak results? A chart must never manufacture, amplify, filter, or resimulate a signal merely to satisfy a visual threshold.

**This check applies to ALL figure types.** Inspect the source values, transformations, row counts, summary statistics, and rendered output together. A flat line, overlapping groups, zero significant features, or AUC near 0.5 can be a legitimate result; report it honestly instead of changing the data.

**How to check per chart type:**

| Chart Type | Integrity check | Pass condition | Failure to flag |
|-----------|-----------------|----------------|-----------------|
| **Volcano** | finite fold changes; adjusted p-values in [0,1]; threshold and multiple-testing method recorded | plotted row count matches the declared filtered count; 0 significant features is allowed | silent row loss, invalid p-values, or a threshold changed after seeing results |
| **AUROC / ROC** | finite monotone FPR/TPR in [0,1]; AUC recomputed from plotted points | reported and recomputed AUC agree within numeric tolerance; a diagonal curve is allowed | fabricated smoothing, impossible coordinates, or label/AUC mismatch |
| **Heatmap** | finite matrix; dimensions and any scaling/clustering recorded | displayed rows/columns and scaling match the source; constant rows are reported, not altered | silent feature removal, per-panel rescaling that changes comparisons, or all-NaN blocks |
| **Bar / Box / Violin** | group n, center statistic, spread definition, and raw-to-summary mapping | bars/distributions reproduce the source groups; equal groups are allowed | SEM/SD/CI mislabeled, hidden groups, or summaries computed from different rows |
| **Correlation matrix** | symmetry, diagonal, value range, missing-data rule, and sample n | coefficients match a recomputation under the stated rule; weak correlations are allowed | mixing pairwise/listwise deletion silently or masking inconvenient values |
| **RDA / PCA** | preprocessing, matrix orientation, component order, and explained variance | plotted scores/loadings and explained-variance labels match the fitted result; overlap is allowed | transposed input, label permutation, or hand-separated groups |
| **Scatter / Regression** | finite x/y pairs, n after filtering, fitted equation and metric | plotted points and reported fit use the same paired rows; weak association is allowed | dropping outliers without disclosure or reporting a metric from another split |
| **Line / Trend** | x ordering, units, aggregation and missingness | plotted order and aggregation match the declared procedure; a flat trend is allowed | implicit sorting, interpolation presented as observation, or clipped extrema |
| **Multi-panel general** | source-to-panel row counts and panel content bounds | each panel is non-empty, legible, and traceable to a declared result file | blank panels, accidental overplotting, or panels backed by different undeclared data versions |

**How to run the check (two-phase):**

**Phase A—data/code check (before rendering):** Recompute each displayed statistic from the declared source rows. Record input count, excluded count with reasons, output count, units, and transformation. A mismatch is FAIL; a scientifically null result is PASS with an honest caption.

**Phase B—render check (after rendering):** Confirm that every expected layer is visible and that axes, clipping, scales, legends, and annotations do not change the meaning. Pixel-content heuristics may raise a WARN for inspection, but they are not evidence that the scientific signal is too weak or too strong.

**Fix if FAIL:**
- Data/code mismatch → trace the transformation and correct the implementation; do not tune the data to the expected picture
- Invalid or non-finite values → correct the upstream computation or disclose and justify the exclusion count
- Legitimate null/weak result → keep it, state the uncertainty and limitation, and reconsider whether this chart adds evidence
- Panel invisible → verify non-empty arrays and axis limits; never replace real values with demo data in a contest deliverable

**Pass condition:** Displayed values reproduce the declared source and computation; every exclusion and transformation is traceable; null results remain unaltered; all rendered panels are visible and semantically faithful.

### Visual Verification Protocol

1. **Render the figure**—run the generated code. If Python/R is not available locally, mark Pass 3 as not run and flag the limitation to the user.
2. **Inspect methodically**—check VV-1 through VV-5 in order. Do not skim; focus on each check individually.
3. **Fix and re-render**—each FAIL requires a code fix AND re-rendering. Fix all VV issues, re-render, and re-inspect. Maximum 3 render-fix cycles.
4. **Escalate if stuck**—if 3 cycles do not resolve the issues, the layout likely needs restructuring. Escalate to Reviewer Simulation Mode for a wider diagnosis.

**Pass 3 report format:**
```
Pass 3 — Visual Verification:
  [PASS] VV-1: No data occlusion
  [FAIL] VV-2: Panel (c) legend extends beyond figure right edge — adjust bbox_to_anchor
  [PASS] VV-3: All text legible at 300dpi
  [WARN] VV-4: Treatment blue (#2166AC) vs Knockout green (#1B7837) distinct but check greyscale
  [FAIL] VV-5: reported AUC differs from the value recomputed from the plotted ROC coordinates
```

---

## QA Report Format

After executing all four passes, output a structured report:

```
============================================================
Academic Figure Skill QA Report
============================================================
Figure: [brief description]
Target: [journal], [single/double] column
Backend: [Python/R]

Pass 0 — Anti-Pattern Scan:
  [PASS] AP-1 Default Color Palette
  [PASS] AP-2 Jet/Rainbow Colormap
  [FAIL] AP-3 Four-Sided Borders — top/right spines not removed
  [PASS] AP-4 Legend Occlusion
  ...

Pass 1 — Code Compliance:
  [PASS] CL-1 Font Size Floor (min 6pt)
  [FAIL] CL-2 Figure Dimensions — width 120 mm, not 89 mm or 183 mm
  ...

Pass 2 — Visual Logic:
  [PASS] VI-1 Core Conclusion Visibility
  [WARN] VI-2 Color Accessibility — red-green pair used, add shape differentiation
  ...

Pass 3 — Visual Verification (render required):
  [PASS] VV-1: No data occlusion
  [PASS] VV-2: Layout regular, panels aligned
  [FAIL] VV-3: Gene labels at 4 pt italic are illegible — increase to 5 pt
  ...

Summary:
  Pass: X/Y   Fail: X/Y   Warn: X/Y

Verdict:
  [READY] — All checks passed. Deliver.
  [FIX] — N failures need attention. Fix and re-run this protocol.
  [WARN] — Deliverable with caveats noted above.

============================================================
```

## After QA

- **READY →** All passes (0–3) clear. Proceed to Hub Step 6 (Deliver). Include the full QA report with delivery.
- **FIX →** Fix failed items, re-run only the failed pass, then re-render for Pass 3 if visual changes were made. Maximum 3 render-fix cycles.
- **WARN →** Deliver with warnings noted. Flag them to the user.
- **NOT RUN: Pass 3 →** If Python/R is unavailable locally, state: "Pass 3 (visual verification) was not run because no local Python/R runtime was available. Please run and visually inspect the output before submission." Do not count it as a pass.

If >2 failures remain after one round of fixes, or Pass 3 issues persist after 3 render-fix cycles, escalate to **Reviewer Simulation Mode** (Hub SKILL.md, Reviewer Simulation section) for a wider diagnosis.

If >2 failures remain after one round of fixes, the figure likely has structural issues. Escalate to **Reviewer Simulation Mode** (Hub SKILL.md, Reviewer Simulation section) for a wider diagnosis before attempting more fixes.
