# Academic Figure Skill Asset Confirmation (verified against assets/figures/)
# (a) modeling evidence route -> assets/figures/<script type>/ -> native run | visual adapt
# RULE: Demo data below is preview-only. Contest figures must map a real result CSV.

# Academic Figure Skill Typography Baseline — COPY VERBATIM, place at TOP of script
import matplotlib as mpl
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans"],
    "axes.unicode_minus": False,
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 8,
    "figure.titlesize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.6,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "legend.frameon": False,
})

# Academic Figure Skill Nature/Cell/Science Color Palette -- COPY VERBATIM
CATEGORICAL = ["#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666"]
CATEGORICAL_EXTENDED = [
    "#2166AC", "#B2182B", "#1B7837", "#F1A340", "#762A83", "#666666",
    "#4393C3", "#D6604D", "#5AAE61", "#B35806", "#9970AB", "#999999",
]
DIVERGING   = ["#2166AC", "#F7F7F7", "#B2182B"]
SEQUENTIAL  = ["#F7FBFF", "#6BAED6", "#08306B"]
ACCENT_RED  = "#B2182B"
GREY        = "#999999"
BLACK       = "#222222"

# Academic Figure Skill Export Baseline — COPY VERBATIM
mpl.rcParams.update({
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.bbox": "tight",
    "savefig.dpi": 300,
})

def save_cns_figure(fig, filename):
    """Standard Academic Figure Skill export: vector PDF + 300dpi PNG preview."""
    fig.savefig(f"{filename}.pdf", bbox_inches="tight", dpi=300)
    fig.savefig(f"{filename}.png", bbox_inches="tight", dpi=300)


import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.font_manager import FontProperties
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


TYPE_BY_STEM = {
    "trajectory_projection": "TrajectoryProjection",
    "parameter_sweep": "ParameterSweep",
    "residual_diagnostics": "ResidualDiagnostics",
    "monte_carlo_recovery": "MonteCarloRecovery",
    "convergence_band": "ConvergenceBand",
    "sensitivity_tornado": "SensitivityTornado",
    "scenario_heatmap": "ScenarioHeatmap",
    "contribution_waterfall": "ContributionWaterfall",
    "phase_profile": "PhaseProfile",
    "resource_design": "ResourceDesign",
}


def configure_chinese_font() -> FontProperties:
    candidates = []
    here = Path(__file__).resolve()
    candidates.extend(parent / "scripts" for parent in here.parents)
    candidates.extend([
        Path.cwd() / ".agents/skills/academic-figure-skill/scripts",
        Path.cwd() / ".claude/skills/academic-figure-skill/scripts",
    ])
    for directory in candidates:
        if (directory / "chinese_fonts.py").is_file():
            sys.path.insert(0, str(directory))
            from chinese_fonts import configure_matplotlib, find_chinese_font
            selected = find_chinese_font()
            if selected is None:
                break
            configure_matplotlib(selected)
            return FontProperties(fname=selected.path)
    raise RuntimeError("未找到 academic-figure-skill 中文字体检测器或可用中文字体")


def demo_data(kind: str) -> pd.DataFrame:
    rng = np.random.default_rng(2026)
    if kind == "TrajectoryProjection":
        t = np.linspace(0, 8 * np.pi, 600)
        return pd.DataFrame({"x": (1 + 0.018*t)*np.cos(t), "y": (1 + 0.018*t)*np.sin(t),
                             "z": 0.45*np.sin(0.5*t), "progress": np.linspace(0, 1, t.size)})
    if kind == "ParameterSweep":
        x, y = np.meshgrid(np.linspace(0.2, 1.8, 45), np.linspace(0.1, 1.5, 40))
        score = np.exp(-((x-1.18)**2/0.16 + (y-0.78)**2/0.12)) - 0.12*(x+y)
        return pd.DataFrame({"parameter_x": x.ravel(), "parameter_y": y.ravel(), "score": score.ravel(),
                             "feasible": (x.ravel()+0.72*y.ravel() <= 2.05)})
    if kind == "ResidualDiagnostics":
        index = np.arange(240)
        residual = 0.18*np.sin(index/13) + rng.normal(0, 0.075, index.size)
        residual[[42, 171]] += [0.42, -0.38]
        return pd.DataFrame({"index": index, "residual": residual, "limit": 0.30})
    if kind == "MonteCarloRecovery":
        truth = rng.uniform(-1.6, 1.6, 900)
        sigma = 0.10 + 0.06*np.abs(truth)
        recovered = truth + rng.normal(0, sigma)
        return pd.DataFrame({"truth": truth, "recovered": recovered, "lower": recovered-1.96*sigma,
                             "upper": recovered+1.96*sigma})
    if kind == "ConvergenceBand":
        iteration = np.arange(1, 181)
        rows = []
        for seed in range(18):
            objective = 0.34 + 1.8*np.exp(-iteration/(24+seed*0.6)) + rng.normal(0, 0.025, iteration.size)
            violation = 0.9*np.exp(-iteration/18) + rng.uniform(0, 0.01, iteration.size)
            rows.extend(zip(iteration, [seed]*iteration.size, objective, violation))
        return pd.DataFrame(rows, columns=["iteration", "seed", "objective", "violation"])
    if kind == "SensitivityTornado":
        names = ["参数 α", "输入噪声", "约束强度", "初始状态", "采样间隔", "阈值 β", "时间窗"]
        effect = np.array([0.31, -0.26, 0.22, -0.18, 0.13, -0.10, 0.07])
        return pd.DataFrame({"parameter": names, "effect": effect, "low": effect-0.035, "high": effect+0.035})
    if kind == "ScenarioHeatmap":
        scenarios = ["基准", "高噪声", "数据缺失", "紧约束", "资源受限", "联合扰动"]
        modules = ["完整模型", "去除校正", "去除鲁棒项", "简化约束", "Baseline"]
        values = 0.92 - rng.uniform(0.00, 0.32, (len(scenarios), len(modules)))
        values[:, 0] += 0.06
        return pd.DataFrame(values, index=scenarios, columns=modules).rename_axis("scenario").reset_index().melt("scenario", var_name="module", value_name="score")
    if kind == "ContributionWaterfall":
        return pd.DataFrame({"component": ["基准项", "几何修正", "传播修正", "系统偏差", "鲁棒补偿"],
                             "contribution": [1.18, 0.42, -0.27, 0.16, -0.11]})
    if kind == "PhaseProfile":
        cycle = np.arange(48)
        phase = np.linspace(0, 1, 96, endpoint=False)
        c, p = np.meshgrid(cycle, phase, indexing="ij")
        intensity = 0.18 + 1.2*np.exp(-((p-0.31-0.001*c)%1)**2/0.0025) + 0.55*np.exp(-((p-0.70)%1)**2/0.008)
        intensity += rng.normal(0, 0.08, intensity.shape)
        return pd.DataFrame({"cycle": c.ravel(), "phase": p.ravel(), "intensity": intensity.ravel()})
    resource = np.linspace(1, 120, 120)
    performance = 0.98*(1-np.exp(-resource/24))
    return pd.DataFrame({"resource": resource, "performance": performance, "cost": 0.18+0.0075*resource})


REQUIRED = {
    "TrajectoryProjection": {"x", "y", "z", "progress"},
    "ParameterSweep": {"parameter_x", "parameter_y", "score", "feasible"},
    "ResidualDiagnostics": {"index", "residual", "limit"},
    "MonteCarloRecovery": {"truth", "recovered", "lower", "upper"},
    "ConvergenceBand": {"iteration", "seed", "objective", "violation"},
    "SensitivityTornado": {"parameter", "effect", "low", "high"},
    "ScenarioHeatmap": {"scenario", "module", "score"},
    "ContributionWaterfall": {"component", "contribution"},
    "PhaseProfile": {"cycle", "phase", "intensity"},
    "ResourceDesign": {"resource", "performance", "cost"},
}


def validate(df: pd.DataFrame, kind: str) -> None:
    missing = REQUIRED[kind] - set(df.columns)
    if missing:
        raise ValueError(f"{kind} 缺少字段: {sorted(missing)}")
    if not np.isfinite(df.select_dtypes(include=[np.number]).to_numpy()).all():
        raise ValueError("数值字段包含 NaN/Inf")


def draw_trajectory(df, prop):
    fig = plt.figure(figsize=(183/25.4, 112/25.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.55, 0.62], hspace=0.30, wspace=0.24)
    ax = fig.add_subplot(gs[:, 0], projection="3d")
    points = ax.scatter(df.x, df.y, df.z, c=df.progress, cmap=LinearSegmentedColormap.from_list("seq", SEQUENTIAL), s=7, alpha=0.85)
    ax.plot(df.x, df.y, df.z, color=CATEGORICAL[0], lw=0.8, alpha=0.5)
    ax.scatter(df.x.iloc[-1], df.y.iloc[-1], df.z.iloc[-1], s=55, marker="*", color=ACCENT_RED, zorder=5)
    ax.set(xlabel="x（单位）", ylabel="y（单位）", zlabel="z（单位）")
    ax.set_title("三维轨迹与关键终点", fontproperties=prop, pad=10)
    ax.view_init(elev=24, azim=38)
    ax.grid(False)
    cbar = fig.colorbar(points, ax=ax, pad=0.08, shrink=0.70); cbar.set_label("归一化进程", fontproperties=prop)
    iax = fig.add_subplot(gs[0, 1]); iax.plot(df.x, df.y, color=CATEGORICAL[4], lw=1.0); iax.scatter(df.x.iloc[-1], df.y.iloc[-1], color=ACCENT_RED, s=18)
    iax.set_title("x-y 投影", fontproperties=prop, fontsize=7); iax.set_aspect("equal"); iax.set_xticks([]); iax.set_yticks([])
    jax = fig.add_subplot(gs[1, 1]); jax.plot(df.x, df.z, color=CATEGORICAL[2], lw=1.0); jax.scatter(df.x.iloc[-1], df.z.iloc[-1], color=ACCENT_RED, s=18)
    jax.set_title("x-z 投影", fontproperties=prop, fontsize=7); jax.set_xticks([]); jax.set_yticks([])
    return fig, {"n": len(df), "endpoint": [float(df.x.iloc[-1]), float(df.y.iloc[-1]), float(df.z.iloc[-1])]}


def draw_sweep(df, prop):
    pivot = df.pivot(index="parameter_y", columns="parameter_x", values="score")
    feasible = df.pivot(index="parameter_y", columns="parameter_x", values="feasible")
    x, y = pivot.columns.to_numpy(), pivot.index.to_numpy()
    fig, ax = plt.subplots(figsize=(183/25.4, 105/25.4))
    cmap = LinearSegmentedColormap.from_list("score", ["#F7FBFF", "#6BAED6", "#762A83", "#B2182B"])
    im = ax.contourf(x, y, pivot.to_numpy(), levels=18, cmap=cmap)
    ax.contour(x, y, feasible.to_numpy(dtype=float), levels=[0.5], colors=BLACK, linewidths=1.2, linestyles="--")
    idx = np.nanargmax(np.where(feasible.to_numpy(), pivot.to_numpy(), np.nan)); iy, ix = np.unravel_index(idx, pivot.shape)
    ax.scatter(x[ix], y[iy], marker="*", s=90, color="#F1A340", edgecolor=BLACK, linewidth=0.5)
    ax.annotate("可行最优点", (x[ix], y[iy]), xytext=(10, 12), textcoords="offset points", fontproperties=prop, arrowprops={"arrowstyle": "->", "lw": 0.7})
    ax.set(xlabel="参数一", ylabel="参数二"); ax.set_title("参数扫描、可行边界与最优区域", fontproperties=prop)
    cbar = fig.colorbar(im, ax=ax, pad=0.02); cbar.set_label("目标值", fontproperties=prop)
    return fig, {"grid": list(pivot.shape), "best": [float(x[ix]), float(y[iy]), float(pivot.iloc[iy, ix])]}


def draw_residual(df, prop):
    fig = plt.figure(figsize=(183/25.4, 92/25.4)); gs = fig.add_gridspec(1, 2, width_ratios=[1.52, 0.45], wspace=0.16)
    ax = fig.add_subplot(gs[0, 0])
    colors = np.where(np.abs(df.residual) > df.limit, ACCENT_RED, np.where(df.residual >= 0, CATEGORICAL[0], CATEGORICAL[4]))
    ax.vlines(df.index, 0, df.residual, color=colors, lw=0.7, alpha=0.72); ax.scatter(df.index, df.residual, c=colors, s=10)
    limit = float(df.limit.iloc[0]); ax.axhspan(-limit, limit, color="#6BAED6", alpha=0.10); ax.axhline(0, color=BLACK, lw=0.7)
    ax.set(xlabel="样本/时刻", ylabel="有符号残差"); ax.set_title("残差结构与容许带", fontproperties=prop)
    iax = fig.add_subplot(gs[0, 1])
    iax.hist(df.residual, bins=24, orientation="horizontal", color=CATEGORICAL[2], alpha=0.75); iax.axhline(0, color=BLACK, lw=0.6)
    iax.set_title("分布", fontproperties=prop, fontsize=7); iax.set_xticks([])
    return fig, {"n": len(df), "rmse": float(np.sqrt(np.mean(df.residual**2))), "violations": int((np.abs(df.residual)>df.limit).sum())}


def draw_recovery(df, prop):
    fig = plt.figure(figsize=(183/25.4, 102/25.4)); gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 0.55], wspace=0.18)
    ax = fig.add_subplot(gs[0, 0])
    hb = ax.hexbin(df.truth, df.recovered, gridsize=34, cmap=LinearSegmentedColormap.from_list("density", ["#F7FBFF", "#4393C3", "#762A83"]), mincnt=1)
    lo, hi = float(min(df.truth.min(), df.recovered.min())), float(max(df.truth.max(), df.recovered.max()))
    ax.plot([lo, hi], [lo, hi], ls="--", color=ACCENT_RED, lw=1.0); ax.set(xlabel="注入真值", ylabel="恢复值", xlim=(lo, hi), ylim=(lo, hi))
    ax.set_title("Monte Carlo 注入—恢复一致性", fontproperties=prop); fig.colorbar(hb, ax=ax, pad=0.02, label="样本密度")
    iax = fig.add_subplot(gs[0, 1])
    error = df.recovered-df.truth; iax.hist(error, bins=28, color=CATEGORICAL[3], alpha=0.82); iax.axvline(0, color=BLACK, lw=0.7)
    iax.set_title("恢复误差", fontproperties=prop, fontsize=7); iax.set_yticks([])
    coverage = ((df.lower <= df.truth) & (df.truth <= df.upper)).mean()
    return fig, {"n": len(df), "bias": float(error.mean()), "rmse": float(np.sqrt(np.mean(error**2))), "coverage": float(coverage)}


def draw_convergence(df, prop):
    grouped = df.groupby("iteration")
    median = grouped.objective.median(); low = grouped.objective.quantile(0.1); high = grouped.objective.quantile(0.9); violation = grouped.violation.median()
    fig, ax = plt.subplots(figsize=(183/25.4, 92/25.4))
    ax.fill_between(median.index, low, high, color=CATEGORICAL[0], alpha=0.18, label="10%--90%")
    ax.plot(median.index, median, color=CATEGORICAL[0], lw=1.8, label="目标函数中位数"); ax.set(xlabel="迭代次数", ylabel="目标函数")
    ax2 = ax.twinx(); ax2.plot(violation.index, violation, color=ACCENT_RED, ls="--", lw=1.1); ax2.set_ylabel("约束违例", color=ACCENT_RED)
    ax.set_title("多随机种子收敛与可行性", fontproperties=prop); ax.legend(bbox_to_anchor=(1.0, 1.15), loc="upper right")
    return fig, {"seeds": int(df.seed.nunique()), "iterations": int(df.iteration.max()), "final_objective": float(median.iloc[-1]), "final_violation": float(violation.iloc[-1])}


def draw_tornado(df, prop):
    ordered = df.reindex(df.effect.abs().sort_values().index)
    y = np.arange(len(ordered)); colors = np.where(ordered.effect >= 0, CATEGORICAL[1], CATEGORICAL[0])
    fig, ax = plt.subplots(figsize=(183/25.4, 94/25.4))
    ax.barh(y, ordered.effect, color=colors, alpha=0.82, height=0.62); ax.errorbar(ordered.effect, y, xerr=[ordered.effect-ordered.low, ordered.high-ordered.effect], fmt="none", ecolor=BLACK, capsize=2, lw=0.7)
    ax.axvline(0, color=BLACK, lw=0.8); ax.set_yticks(y, ordered.parameter, fontproperties=prop); ax.set_xlabel("输出相对变化"); ax.set_title("局部灵敏度排序及区间", fontproperties=prop)
    for yi, value in zip(y, ordered.effect): ax.text(value + np.sign(value)*0.012, yi, f"{value:+.2f}", va="center", ha="left" if value > 0 else "right", fontsize=7)
    return fig, {"parameters": len(df), "most_sensitive": str(ordered.iloc[-1].parameter), "max_abs_effect": float(ordered.iloc[-1].effect)}


def draw_scenario(df, prop):
    pivot = df.pivot(index="scenario", columns="module", values="score")
    fig, ax = plt.subplots(figsize=(183/25.4, 104/25.4))
    cmap = LinearSegmentedColormap.from_list("scenario", ["#B2182B", "#F7F7F7", "#2166AC"])
    norm = TwoSlopeNorm(vmin=float(pivot.min().min()), vcenter=float(pivot.stack().median()), vmax=float(pivot.max().max()))
    im = ax.imshow(pivot, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=25, ha="right", fontproperties=prop); ax.set_yticks(range(len(pivot.index)), pivot.index, fontproperties=prop)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]): ax.text(j, i, f"{pivot.iloc[i,j]:.2f}", ha="center", va="center", fontsize=7, color=BLACK)
    ax.set_title("场景—模块消融响应矩阵", fontproperties=prop); fig.colorbar(im, ax=ax, pad=0.02, label="性能")
    best = np.unravel_index(np.argmax(pivot.to_numpy()), pivot.shape); ax.scatter(best[1], best[0], marker="*", s=90, facecolor="#F1A340", edgecolor=BLACK)
    return fig, {"shape": list(pivot.shape), "best": [str(pivot.index[best[0]]), str(pivot.columns[best[1]]), float(pivot.iloc[best])]}


def draw_waterfall(df, prop):
    cumulative = np.r_[0, df.contribution.cumsum().to_numpy()[:-1]]; end = cumulative + df.contribution.to_numpy()
    colors = [CATEGORICAL[0] if v >= 0 else ACCENT_RED for v in df.contribution]
    fig, ax = plt.subplots(figsize=(183/25.4, 88/25.4))
    ax.bar(np.arange(len(df)), df.contribution.abs(), bottom=np.minimum(cumulative, end), color=colors, alpha=0.84, width=0.68)
    for i in range(len(df)-1): ax.plot([i+0.34, i+0.66], [end[i], end[i]], color=GREY, lw=0.8)
    ax.axhline(0, color=BLACK, lw=0.7); ax.set_xticks(range(len(df)), df.component, rotation=18, ha="right", fontproperties=prop); ax.set_ylabel("累计贡献"); ax.set_title("有符号分量贡献瀑布图", fontproperties=prop)
    for i, (bottom, value) in enumerate(zip(cumulative, df.contribution)): ax.text(i, bottom+value/2, f"{value:+.2f}", ha="center", va="center", fontsize=7, color="white")
    return fig, {"components": len(df), "total": float(df.contribution.sum())}


def draw_phase(df, prop):
    pivot = df.pivot(index="cycle", columns="phase", values="intensity"); profile = pivot.mean(axis=0)
    fig = plt.figure(figsize=(183/25.4, 100/25.4)); gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.0], wspace=0.28)
    ax = fig.add_subplot(gs[0]); im = ax.imshow(pivot, aspect="auto", origin="lower", extent=[0,1,pivot.index.min(),pivot.index.max()], cmap=LinearSegmentedColormap.from_list("phase", ["#F7FBFF", "#4393C3", "#762A83", "#B2182B"]))
    ax.set(xlabel="相位", ylabel="周期编号"); ax.set_title("相位栅格", fontproperties=prop); fig.colorbar(im, ax=ax, pad=0.02, label="强度")
    ax2 = fig.add_subplot(gs[1]); ax2.fill_between(profile.index, profile, color=CATEGORICAL[4], alpha=0.24); ax2.plot(profile.index, profile, color=CATEGORICAL[4], lw=1.5); ax2.axvline(float(profile.idxmax()), color=ACCENT_RED, ls="--", lw=0.9)
    ax2.set(xlabel="相位", ylabel="平均轮廓"); ax2.set_title("折叠周期轮廓", fontproperties=prop)
    return fig, {"cycles": int(pivot.shape[0]), "bins": int(pivot.shape[1]), "peak_phase": float(profile.idxmax())}


def draw_resource(df, prop):
    utility = df.performance - 0.55*df.cost; knee_idx = int(np.argmax(utility))
    fig, ax = plt.subplots(figsize=(183/25.4, 90/25.4))
    ax.plot(df.resource, df.performance, color=CATEGORICAL[0], lw=1.8); ax.fill_between(df.resource, 0, df.performance, color=CATEGORICAL[0], alpha=0.10)
    ax.axvspan(df.resource.iloc[knee_idx], df.resource.max(), color=CATEGORICAL[2], alpha=0.08); ax.scatter(df.resource.iloc[knee_idx], df.performance.iloc[knee_idx], marker="*", s=90, color="#F1A340", edgecolor=BLACK)
    ax.annotate("推荐拐点", (df.resource.iloc[knee_idx], df.performance.iloc[knee_idx]), xytext=(12,-25), textcoords="offset points", fontproperties=prop, arrowprops={"arrowstyle":"->", "lw":0.7})
    ax.set(xlabel="资源/观测时长", ylabel="预期性能", ylim=(0,1.03)); ax.set_title("资源需求、收益饱和与推荐设计", fontproperties=prop)
    ax2 = ax.twinx(); ax2.plot(df.resource, df.cost, color=CATEGORICAL[3], ls="--", lw=1.0); ax2.set_ylabel("归一化成本", color=CATEGORICAL[3])
    return fig, {"n": len(df), "knee_resource": float(df.resource.iloc[knee_idx]), "knee_performance": float(df.performance.iloc[knee_idx])}


DRAW = {
    "TrajectoryProjection": draw_trajectory, "ParameterSweep": draw_sweep,
    "ResidualDiagnostics": draw_residual, "MonteCarloRecovery": draw_recovery,
    "ConvergenceBand": draw_convergence, "SensitivityTornado": draw_tornado,
    "ScenarioHeatmap": draw_scenario, "ContributionWaterfall": draw_waterfall,
    "PhaseProfile": draw_phase, "ResourceDesign": draw_resource,
}


def main() -> None:
    stem = Path(__file__).stem
    parser = argparse.ArgumentParser(description="Huawei Cup modeling production figure asset")
    parser.add_argument("--data", type=Path, help="Real result CSV; omit only for asset preview")
    parser.add_argument("--output-prefix", type=Path)
    parser.add_argument("--kind", choices=sorted(DRAW), default=TYPE_BY_STEM.get(stem))
    args = parser.parse_args()
    if args.kind is None:
        raise SystemExit(f"Unknown script stem {stem}; pass --kind")
    prop = configure_chinese_font()
    df = pd.read_csv(args.data) if args.data else demo_data(args.kind)
    validate(df, args.kind)
    fig, stats = DRAW[args.kind](df, prop)
    fig.canvas.draw()
    output = (args.output_prefix or Path(__file__).with_suffix("")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    save_cns_figure(fig, str(output))
    plt.close(fig)
    report = {"kind": args.kind, "data": str(args.data) if args.data else "DEMO_PREVIEW_ONLY", "rows": len(df), "statistics": stats}
    output.with_suffix(".stats.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(output), **report}, ensure_ascii=False))


if __name__ == "__main__":
    main()
