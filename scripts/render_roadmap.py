#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_roadmap.py — 技术路线图（论文图1）渲染器。

读取 YAML 规格（assets/roadmap/roadmap.schema.json），按"输入→预处理→模型→求解→
验证→输出"六层分层布局，用 matplotlib 绘制 FancyBboxPatch 节点 + FancyArrowPatch 边，
同时导出 PNG / PDF（矢量）/ Mermaid(.mmd) / Graphviz(.dot) 四种格式。

色盲友好配色复用 skills/academic-figure 语义色板；中文字体优先 Microsoft YaHei，
系统无任何 CJK 字体时自动切换节点 label_en 英文标签优雅回退，不崩溃。

用法：
    python scripts/render_roadmap.py --spec roadmap.yaml --outdir out --fmt png,pdf,mmd,dot
    python scripts/render_roadmap.py --spec roadmap.yaml --title "自定义标题"
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

# ---- 色盲友好配色（与 skills/academic-figure/references/color-palettes.md 一致）----
# 语义角色：蓝=输入/基准  浅蓝=预处理  绿=模型/治疗  橙=求解  紫=验证  红=输出/强调(小面积)
LAYER_COLORS: dict[str, str] = {
    "input": "#2166AC",
    "preprocess": "#4393C3",
    "model": "#1B7837",
    "solve": "#F1A340",
    "validate": "#762A83",
    "output": "#B2182B",
}
# 允许出现在图上的色盲友好色板（校验器同源；禁止 jet/rainbow/tab10/Set1）
CBF_SAFE_COLORS = set(LAYER_COLORS.values()) | {
    "#D6604D", "#5AAE61", "#B35806", "#9970AB", "#999999", "#666666", "#222222",
}
DASHED_GREY = "#666666"

CJK_CANDIDATES = [
    "Microsoft YaHei", "SimHei", "Microsoft JhengHei", "PingFang SC",
    "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Zen Hei", "DengXian",
]


def load_spec(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def detect_cjk_font() -> tuple[str | None, bool]:
    """返回 (字体名, 是否有 CJK)。无 CJK 时用 None 并切英文标签回退。"""
    try:
        from matplotlib import font_manager
    except Exception:  # pragma: no cover - matplotlib 必装
        return None, False
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in CJK_CANDIDATES:
        if name in installed:
            return name, True
    # 模糊兜底：名字里含 CJK 关键字
    keys = ("yahei", "simhei", "noto sans cjk", "source han", "wenquanyi", "dengxian", "pingfang")
    for f in installed:
        low = f.lower()
        if any(k in low for k in keys):
            return f, True
    return None, False


def setup_matplotlib(has_cjk: bool, font_name: str | None):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import rcParams
    rcParams["axes.unicode_minus"] = False
    if has_cjk and font_name:
        rcParams["font.sans-serif"] = [font_name, "DejaVu Sans"]
    else:
        # 无 CJK：用 DejaVu，节点走 label_en；层标题走英文 id；抑制缺字形告警
        rcParams["font.sans-serif"] = ["DejaVu Sans"]
        import warnings
        warnings.filterwarnings("ignore", message="Glyph .* missing from font")


def node_text(node: dict, has_cjk: bool) -> str:
    """有 CJK：中文 label + method 两行；无 CJK：英文 label_en（无则 label 兜底，不崩溃）。"""
    if has_cjk:
        label = node.get("label", "")
        method = node.get("method", "")
        return f"{label}\n{method}" if method else label
    return node.get("label_en") or node.get("label", "")


def render(spec: dict, outdir: Path, fmts: list[str], title_override: str | None = None) -> dict:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

    font_name, has_cjk = detect_cjk_font()
    setup_matplotlib(has_cjk, font_name)

    meta = spec.get("metadata", {})
    title = title_override or meta.get("title", "技术路线图")
    layers = sorted(spec.get("layers", []), key=lambda L: L.get("order", 0))
    layer_order = {L["id"]: i for i, L in enumerate(layers)}
    layer_label = {L["id"]: L.get("label", L["id"]) for L in layers}
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])

    # 按层分列，列内按定义顺序纵向堆叠
    col_of: dict[str, int] = {}
    row_of: dict[str, float] = {}
    rows_per_col: dict[int, int] = {}
    pos: dict[str, tuple[float, float]] = {}
    col_w, row_h = 2.4, 1.15
    for n in nodes:
        lid = n["layer"]
        ci = layer_order.get(lid, len(layers))
        col_of[n["id"]] = ci
        r = rows_per_col.get(ci, 0)
        row_of[n["id"]] = r
        rows_per_col[ci] = r + 1
        pos[n["id"]] = (ci * col_w, -r * row_h)

    n_cols = max(col_of.values()) + 1 if col_of else 1
    n_rows = max(rows_per_col.values()) if rows_per_col else 1

    fig_w = max(9.0, n_cols * 2.6)
    fig_h = max(5.0, n_rows * 1.25 + 1.8)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(-col_w * 0.5, (n_cols - 1) * col_w + col_w * 0.5)
    ax.set_ylim(-(n_rows - 1) * row_h - row_h * 0.6, row_h * 0.9)
    ax.axis("off")

    # 层底带标签（顶部）。无 CJK 时用英文层 id 回退
    for L in layers:
        ci = layer_order.get(L["id"], 0)
        layer_text = layer_label[L["id"]] if has_cjk else L["id"].upper()
        ax.text(ci * col_w, row_h * 0.55, layer_text,
                ha="center", va="center", fontsize=11, fontweight="bold", color="#222222")

    bw, bh = col_w * 0.82, row_h * 0.62
    drawn: dict[str, FancyBboxPatch] = {}
    for n in nodes:
        x, y = pos[n["id"]]
        fill = n.get("color") or LAYER_COLORS.get(n["layer"], "#666666")
        patch = FancyBboxPatch((x - bw / 2, y - bh / 2), bw, bh,
                               boxstyle="round,pad=0.02,rounding_size=0.08",
                               linewidth=1.2, edgecolor="#222222", facecolor=fill, alpha=0.92)
        ax.add_patch(patch)
        drawn[n["id"]] = patch
        ax.text(x, y, node_text(n, has_cjk), ha="center", va="center",
                fontsize=8.6, color="white", fontweight="bold", wrap=True)

    # 边
    for e in edges:
        a, b = e.get("from"), e.get("to")
        if a not in pos or b not in pos:
            continue
        dashed = e.get("type") == "dashed"
        rad = -0.25 if dashed else 0.0
        arrow = FancyArrowPatch(pos[a], pos[b],
                                arrowstyle="-|>", mutation_scale=13,
                                connectionstyle=f"arc3,rad={rad}",
                                linewidth=1.3,
                                linestyle=(0, (5, 3)) if dashed else "-",
                                color=DASHED_GREY if dashed else "#444444",
                                shrinkA=14, shrinkB=14, zorder=1)
        ax.add_patch(arrow)
        if e.get("label"):
            mx, my = (pos[a][0] + pos[b][0]) / 2, (pos[a][1] + pos[b][1]) / 2
            ax.text(mx, my + (0.18 if dashed else -0.22), e["label"],
                    ha="center", va="center", fontsize=8.2, color=DASHED_GREY,
                    style="italic",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))

    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    fig.tight_layout()

    outdir.mkdir(parents=True, exist_ok=True)
    stem = (meta.get("track") or "roadmap").replace(" ", "_") + "_roadmap"
    written: dict[str, str] = {}

    if "png" in fmts:
        png_path = outdir / f"{stem}.png"
        fig.savefig(png_path, dpi=150, bbox_inches="tight", facecolor="white")
        written["png"] = str(png_path)
    if "pdf" in fmts:
        pdf_path = outdir / f"{stem}.pdf"
        fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
        written["pdf"] = str(pdf_path)
    plt.close(fig)

    if "mmd" in fmts:
        written["mmd"] = _write_mermaid(spec, outdir / f"{stem}.mmd", title, has_cjk)
    if "dot" in fmts:
        written["dot"] = _write_dot(spec, outdir / f"{stem}.dot")

    return {"written": written, "has_cjk_font": has_cjk, "font": font_name}


def _mmd_quote(s: str) -> str:
    return s.replace('"', "'")


def _write_mermaid(spec: dict, path: Path, title: str, has_cjk: bool) -> str:
    nodes = spec.get("nodes", [])
    lines = ["%% 技术路线图（论文图1）— Mermaid 源码，可在 Markdown/在线编辑器继续编辑",
             f"%% title: {title}",
             "flowchart LR"]
    for n in nodes:
        txt = n["label"] if has_cjk else (n.get("label_en") or n["label"])
        method = n.get("method", "")
        label = f"{txt}<br/>{method}" if has_cjk else txt
        lines.append(f'    {n["id"]}["{_mmd_quote(label)}"]')
    for e in spec.get("edges", []):
        if e.get("type") == "dashed":
            lab = f' -- "{_mmd_quote(e.get("label",""))}"' if e.get("label") else ""
            lines.append(f'    {e["from"]} -.->|{lab.strip("-").strip() or "迭代"}| {e["to"]}' if lab
                         else f'    {e["from"]} -.-> {e["to"]}')
        else:
            lab = f'|"{_mmd_quote(e["label"])}"|' if e.get("label") else ""
            lines.append(f"    {e['from']} -->{lab} {e['to']}")
    # 层配色 classDef
    for lid, color in LAYER_COLORS.items():
        lines.append(f'    classDef {lid} fill:{color},stroke:#222222,color:#fff;')
    for n in nodes:
        lines.append(f"    {n['id']}:::{n['layer']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def _write_dot(spec: dict, path: Path) -> str:
    lines = ['digraph roadmap {', '  rankdir=LR;', '  node [shape=box, style="rounded,filled", fontname="DejaVu Sans", fontsize=10];']
    for n in spec.get("nodes", []):
        fill = n.get("color") or LAYER_COLORS.get(n["layer"], "#666666")
        label = f'{n["label"]}\\n{n.get("method","")}'
        label = label.replace('"', '\\"')
        lines.append(f'  {n["id"]} [label="{label}", fillcolor="{fill}", fontcolor="white"];')
    for e in spec.get("edges", []):
        attr = ""
        if e.get("type") == "dashed":
            lab = (e.get("label") or "迭代").replace('"', '\\"')
            attr = f' [style=dashed, label="{lab}", color="#666666", fontcolor="#666666"]'
        lines.append(f'  {e["from"]} -> {e["to"]}{attr};')
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", type=Path, required=True, help="YAML 路线图规格")
    parser.add_argument("--outdir", type=Path, required=True, help="输出目录")
    parser.add_argument("--fmt", type=str, default="png,pdf,mmd,dot",
                        help="逗号分隔输出格式：png,pdf,mmd,dot（默认全部）")
    parser.add_argument("--title", type=str, default=None, help="覆盖 spec 中的标题")
    args = parser.parse_args()

    spec = load_spec(args.spec)
    fmts = [f.strip().lower() for f in args.fmt.split(",") if f.strip()]
    result = render(spec, args.outdir.resolve(), fmts, args.title)
    print("[render_roadmap] CJK 字体:", result["font"] or "无（已切英文标签回退）")
    for k, v in result["written"].items():
        print(f"  -> {k}: {v}")


if __name__ == "__main__":
    main()
