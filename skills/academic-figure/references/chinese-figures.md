# Chinese Figure Text and Anti-Garbled QA

This project keeps the academic-figure-skill layout, color, statistics and
export logic, while adapting ordinary scientific result text to Chinese.
Copy the production script into the working directory before changing only
render-layer labels or data paths. Never change original field names or raw
files.

1. Resolve an installed Chinese-capable font with
   `scripts/chinese_fonts.py`; verify glyph coverage rather than trusting a
   family name.
2. Python figures use `FontProperties`, a concrete fallback stack,
   `axes.unicode_minus=False`, and `fig.canvas.draw()` before export.
3. R figures detect fonts with `systemfonts`/equivalent and use Cairo for
   PNG/PDF rendering.
4. Run the smoke test for Chinese labels, units, RMSE, negative values, Greek
   letters and subscripts. Inspect PNG/PDF for missing glyphs, overlap,
   clipping, scaling and grayscale readability.
5. Missing fonts, failed glyph coverage or failed render QA are **incomplete**
   and cannot enter the formal image directory or paper.

Flowcharts and model-structure diagrams remain on the Huawei Cup Flowchart
Plan + TikZ/XeLaTeX route; this layer does not replace that gate.
