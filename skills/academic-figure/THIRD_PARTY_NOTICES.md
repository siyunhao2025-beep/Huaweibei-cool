# Third-party notices

The Apache-2.0 license in this directory applies only to material that the
Academic Figure Skill contributors are entitled to license under Apache-2.0.
It does **not** relicense the third-party files listed below.

## figures4papers

- Upstream: [ChenLiu-1996/figures4papers](https://github.com/ChenLiu-1996/figures4papers)
- Audited revision: [`3c181f85e82c6f24948fcaaf3be6696102b41d8d`](https://github.com/ChenLiu-1996/figures4papers/tree/3c181f85e82c6f24948fcaaf3be6696102b41d8d)
- Credit: Chen Liu and figures4papers contributors
- Upstream license: [Creative Commons Attribution-NonCommercial 4.0 International](LICENSES/CC-BY-NC-4.0.txt)
- Source license page: <https://creativecommons.org/licenses/by-nc/4.0/>

CC BY-NC 4.0 requires attribution, a license link, and an indication of
changes, and restricts use to noncommercial purposes. The repository-level
MIT license and this directory's Apache-2.0 license do not remove those
conditions. Users must make their own use-case determination; inclusion in
this repository is not a grant for commercial use.

A 2026-09-24 audit found 17 byte-identical Python files and three adapted
files from the locked upstream revision. The machine-readable inventory is
[`references/figures4papers.lock.json`](references/figures4papers.lock.json).
The following table is the human-readable attribution and change record.

| Upstream file | File in this repository | Status / change indication |
|---|---|---|
| `figure_Brainteaser/plot_brute_force.py` | `assets/figures/BarComposition/plot_brute_force.py` | Byte-identical at audit |
| `figure_Brainteaser/plot_correctness_by_category.py` | `assets/figures/BarCategorical/plot_correctness_by_category.py` | Byte-identical at audit |
| `figure_Brainteaser/plot_correctness_by_subcategory.py` | `assets/figures/BarCategorical/plot_correctness_by_subcategory.py` | Byte-identical at audit |
| `figure_Brainteaser/plot_rewriting.py` | `assets/figures/BarComposition/plot_rewriting.py` | Byte-identical at audit |
| `figure_Brainteaser/plot_selfcorrection_math.py` | `assets/figures/BarDistribution/plot_selfcorrection_math.py` | Byte-identical at audit |
| `figure_CellSpliceNet/plot_ablation.py` | `assets/figures/BarAblation/plot_bar_ablation.py` | Renamed; byte-identical at audit |
| `figure_Cflows/diffusion_swiss_roll.py` | `assets/figures/Manifold/diffusion_swiss_roll.py` | Byte-identical at audit |
| `figure_Cflows/plot_comparison_Ablation.py` | `assets/figures/BarAblation/plot_comparison_ablation.py` | Renamed; byte-identical at audit |
| `figure_Cflows/plot_comparison_GeneRegulatory.py` | `assets/figures/BarComparison/plot_comparison_GeneRegulatory.py` | Byte-identical at audit |
| `figure_Cflows/plot_comparison_Trajectory.py` | `assets/figures/BarComparison/plot_comparison_Trajectory.py` | Byte-identical at audit |
| `figure_ImmunoStruct/plot_bars.py` | `assets/figures/BarAblation/plot_bars_ablation.py` | Renamed; byte-identical at audit |
| `figure_ImmunoStruct/raw_data.py` | `assets/figures/BarComparison/raw_data.py` | Byte-identical at audit |
| `figure_RNAGenScape/plot_comparison.py` | `assets/figures/heatmap/plot_comparison.py` | Byte-identical at audit |
| `figure_RNAGenScape/plot_hole_manifold.py` | `assets/figures/Manifold/plot_hole_manifold.py` | Byte-identical at audit |
| `figure_RNAGenScape/plot_manifold.py` | `assets/figures/Manifold/plot_manifold.py` | Byte-identical at audit |
| `figure_VIGIL/plot_comparison_radar.py` | `assets/figures/Radar/plot_comparison_radar.py` | Byte-identical at audit |
| `figure_ophthal_review/plot_composition.py` | `assets/figures/heatmap/plot_composition.py` | Byte-identical at audit |
| `figure_RNAGenScape/plot_sweep.py` | `assets/figures/LineTrend/plot_sweep.py` | Adapted; differs from upstream |
| `figure_VIGIL/plot_posttraining.py` | `assets/figures/LineTrend/plot_posttraining.py` | Adapted; differs from upstream |
| `figure_ophthal_review/plot_trend.py` | `assets/figures/LineTrend/plot_trend.py` | Adapted; differs from upstream |

The upstream PNG/PDF outputs, paper data, and composite raster assets are not
imported by this integration. They remain reference-only because their
editable sources and possible co-author, publisher, icon, or rendering rights
cannot be established from the repository alone.

## Independently installed `scientific-figure-making` skill

The real upstream skill at `scientific-figure-making/` is distributed as the
independent sibling directory
[`../scientific-figure-making/`](../scientific-figure-making/). Its `SKILL.md`
and five references remain CC BY-NC 4.0; neither this directory's Apache-2.0
license nor the repository-level MIT license applies to that content.

The source, locked blob identifiers, license link, and change record are in
[`../scientific-figure-making/SOURCE.md`](../scientific-figure-making/SOURCE.md).
Four references are redistributed unchanged. `SKILL.md` is adapted only to
route through this repository's license/safety gate, and `references/demos.md`
is adapted only to pin moving `main` links to the audited revision. The added
`SOURCE.md` and `agents/openai.yaml` are integration metadata. These changes do
not grant commercial permission or imply upstream endorsement.
