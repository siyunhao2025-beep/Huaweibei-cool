# -*- coding: utf-8 -*-
"""
华为杯语料卡片聚合脚本（Wave2A 任务一）。
只读 corpus/cards/brief/*.json 与 corpus/cards/deep/*.json、corpus/papers_index.json。
子命令：
  python scripts/corpus_cards.py --stats
产出：
  corpus/method_frequency.json
  corpus/track_archetype_matrix.json
  corpus/cards/AGGREGATE_STATS.md
"""
import os, sys, json, re, glob, collections, argparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BRIEF_DIR = os.path.join(ROOT, "corpus", "cards", "brief")
DEEP_DIR = os.path.join(ROOT, "corpus", "cards", "deep")
INDEX_JSON = os.path.join(ROOT, "corpus", "papers_index.json")

ARCHETYPES = [
    "optimization", "evaluation", "prediction", "classification-cv",
    "mechanism", "signal", "spatial-graph", "simulation",
]

# ---------- 方法同义词归一化 ----------
# key 为正则（小写化后匹配），value 为统一规范名。按优先级从长到短匹配。
METHOD_SYNONYMS = [
    # 优化类
    (r"\bnsga-?ii?\b|非支配排序遗传|多目标遗传|moga|moea/d|多目标进化", "NSGA-II/多目标进化"),
    (r"遗传算法|\bga\b|genetic algorithm|遗传规划", "遗传算法(GA)"),
    (r"粒子群|\bpso\b|particle swarm", "粒子群优化(PSO)"),
    (r"模拟退火|\bsa\b|simulated annealing", "模拟退火(SA)"),
    (r"蚁群|\baco\b|ant colony", "蚁群算法(ACO)"),
    (r"人工蜂群|\babc\b|蜂群", "人工蜂群(ABC)"),
    (r"差分进化|\bde\b|differential evolution", "差分进化(DE)"),
    (r"灰狼|\bgwo\b|gray wolf", "灰狼优化(GWO)"),
    (r"鲸鱼|\bwoa\b|whale", "鲸鱼优化(WOA)"),
    (r"禁忌搜索|\bts\b|tabu|taboo", "禁忌搜索(TS)"),
    (r"线性规划|\blp\b|linear programming|单纯形", "线性规划(LP)"),
    (r"整数规划|0-?1整数|0/1规划|mip|milp|混合整数|ilp|整数线性", "整数规划/混合整数规划"),
    (r"非线性规划|非线性优化|nlp", "非线性规划(NLP)"),
    (r"动态规划", "动态规划(DP)"),
    (r"列生成", "列生成"),
    (r"启发式|贪婪|贪心|构造式", "启发式/贪心"),
    (r"鲁棒优化|鲁棒控制|robust", "鲁棒优化"),
    (r"强化学习|\brl\b|深度强化学习|dqn|q-?learning|actor.critic", "强化学习(RL)"),
    (r"贝叶斯优化", "贝叶斯优化(BO)"),
    (r"排队论|排队模型", "排队论"),
    # 评价类
    (r"层次分析法|\bahp\b|analytic hierarchy", "层次分析法(AHP)"),
    (r"熵权|entropy weight|\bewm\b", "熵权法(EWM)"),
    (r"topsis|逼近理想解", "TOPSIS"),
    (r"模糊综合|模糊评价|fuzzy comprehensive|模糊评判", "模糊综合评价"),
    (r"灰色关联|灰色关联分析", "灰色关联分析(GRA)"),
    (r"主成分分析|\bpca\b|principal component", "主成分分析(PCA)"),
    (r"因子分析", "因子分析(FA)"),
    (r"dea|数据包络", "数据包络分析(DEA)"),
    (r"独立成分|ica\b", "独立成分分析(ICA)"),
    (r"综合评价|综合评判|评价模型", "综合评价"),
    # 预测/回归
    (r"arima|sarima|arma|prophet|指数平滑|\bets\b|holt", "ARIMA/SARIMA时序"),
    (r"灰色预测|gm\(1,1\)|gm11|灰色模型", "灰色预测GM(1,1)"),
    (r"支持向量回归|\bsvr\b", "支持向量回归(SVR)"),
    (r"支持向量机|\bsvm\b", "支持向量机(SVM)"),
    (r"随机森林|\brf\b", "随机森林(RF)"),
    (r"xgboost|xgb", "XGBoost"),
    (r"lightgbm", "LightGBM"),
    (r"梯度提升|gbdt|adaboost|boosting", "GBDT/Boosting族"),
    (r"决策树", "决策树(DT)"),
    (r"逻辑回归|logistic regression|logit", "逻辑回归"),
    (r"多元线性回归|线性回归|岭回归|lasso|偏最小二乘|pls\b|回归分析", "线性/岭/Lasso回归"),
    (r"bp神经网络|bp网络|反向传播神经网络|\bbp\b|反向传播", "BP神经网络"),
    (r"卷积神经网络|\bcnn\b|u-?net|unet|yolo|faster r-?cnn|rcnn", "CNN/目标检测"),
    (r"循环神经网络|\brnn\b|lstm|gru|conv-?lstm|注意力机制|attention|transformer|swin", "RNN/LSTM/Transformer"),
    (r"生成对抗|\bgan\b|扩散模型|diffusion", "GAN/扩散模型"),
    (r"神经网络|人工神经网络|\bnn\b|mlp|多层感知|深度学习|深度网络", "通用神经网络/DL"),
    (r"k-?means|k均值|k中心|聚类分析|层次聚类|系统聚类|fcm|模糊聚类|dbscan|birch", "聚类(K-means/FCM/DBSCAN)"),
    (r"马尔可夫|马尔可夫链|markov|隐马尔可夫|hmm", "马尔可夫链"),
    (r"weibull|威布尔", "Weibull分布"),
    (r"生存分析|cox\b", "生存分析/Cox"),
    (r"小波|wavelet|ceemd|eemd|emd\b", "小波/经验模态分解"),
    # 机理
    (r"微分方程|偏微分方程|\bpde\b|\bod\b|动力学方程|常微分", "微分方程/动力学模型"),
    (r"传染病模型|\bsir\b|\bseir\b|\bsis\b", "传染病模型(SIR/SEIR)"),
    (r"分岔|分岔图|hopf\b|稳定性分析|相图", "分岔/稳定性分析"),
    (r"系统动力学", "系统动力学(SD)"),
    (r"lotka|volterra|捕食", "Lotka-Volterra种群模型"),
    (r"动力学", "动力学模型"),
    # 信号
    (r"music|doa|波达方向|阵列信号|波束形成|dbf|cbf|mvdr|阵列天线", "DOA/阵列信号(MUSIC/MVDR)"),
    (r"压缩感知|稀疏恢复|\bomp\b|正交匹配追踪|稀疏表示|\bsbl\b", "压缩感知/OMP"),
    (r"fft|快速傅里叶|傅里叶变换|频谱分析|频谱", "FFT/频谱分析"),
    (r"滤波|卡尔曼|\bkalman\b|维纳", "滤波/卡尔曼"),
    (r"雷达|回波|fmcw", "雷达信号"),
    (r"脑电|\beeg\b", "脑电信号(EEG)"),
    # 空间/图
    (r"图论|最短路径|dijkstra|拓扑|\bdag\b|有向图|网络流|最大流|最小割|最大团|连通分量|并查集", "图论/网络流"),
    (r"gis|地理信息|空间分析|空间布局|选址|定位|路径规划|车辆路径|\bvrp\b", "空间/GIS/选址/路径"),
    (r"元胞自动机|\bca\b|cellular automata", "元胞自动机"),
    # 仿真
    (r"蒙特卡洛|monte carlo|随机模拟", "蒙特卡洛模拟"),
    (r"离散事件|离散事件仿真|系统仿真|多智能体|agent仿真|仿真模型|仿真器", "系统/多智能体仿真"),
    (r"排队论", "排队论"),
]
METHOD_PATTERNS = [(re.compile(p, re.IGNORECASE), norm) for p, norm in METHOD_SYNONYMS]

# 未命中时的兜底正则
FALLBACK_METHOD_PATTERNS = [
    (re.compile(r"回归", re.IGNORECASE), "回归分析"),
    (re.compile(r"预测", re.IGNORECASE), "预测模型"),
    (re.compile(r"优化", re.IGNORECASE), "优化方法"),
    (re.compile(r"评价", re.IGNORECASE), "评价方法"),
    (re.compile(r"分类", re.IGNORECASE), "分类方法"),
]

# ---------- 原型触发关键词 ----------
ARCH_TRIGGERS = {
    "optimization": [
        r"优化", r"线性规划", r"整数规划", r"0-?1", r"排样", r"调度", r"选址", r"背包",
        r"遗传", r"粒子群", r"模拟退火", r"蚁群", r"nsga", r"多目标", r"启发式", r"贪心",
        r"列生成", r"动态规划", r"鲁棒优化", r"强化学习", r"贝叶斯优化", r"目标函数",
        r"分配", r"布局", r"内存预算", r"排程", r"下料", r"运输", r"路径",
    ],
    "evaluation": [
        r"ahp", r"层次分析", r"熵权", r"topsis", r"模糊综合", r"灰色关联", r"主成分",
        r"因子分析", r"评价", r"权重", r"打分", r"评级", r"综合评判", r"指标体系",
        r"数据包络", r"dea", r"优劣解", r"排名",
    ],
    "prediction": [
        r"预测", r"预报", r"时间序列", r"arima", r"lstm", r"回归", r"灰色预测",
        r"prophet", r"随机森林", r"xgboost", r"svr", r"支持向量", r"时序", r"外推",
        r"负荷", r"销量", r"故障诊断.*预测", r"趋势", r"建模.*预测",
    ],
    "classification-cv": [
        r"分类", r"支持向量机", r"随机森林", r"决策树", r"cnn", r"卷积", r"yolo",
        r"图像处理", r"模式识别", r"目标检测", r"图像分割", r"分割", r"迁移学习",
        r"故障诊断", r"识别", r"聚类", r"dbscan", r"k-?means", r"fc m", r"二分类",
        r"多分类", r"knn", r"感知机",
    ],
    "mechanism": [
        r"微分方程", r"动力学", r"偏微分", r"传染病", r"分岔", r"物理建模", r"机理",
        r"系统动力学", r"sir", r"seir", r"种群", r"lotka", r"振动", r"流体",
        r"扩散方程", r"热传导", r"反应扩散",
    ],
    "signal": [
        r"频谱", r"滤波", r"雷达", r"fft", r"music", r"doa", r"压缩感知", r"脑电",
        r"小波", r"波束", r"阵列", r"回波", r"信号处理", r"正交匹配", r"omp",
        r"傅里叶", r"多普勒",
    ],
    "spatial-graph": [
        r"空间布局", r"图论", r"网络", r"路径规划", r"gis", r"最短路径", r"拓扑",
        r"dag", r"有向图", r"网络流", r"地理", r"空间分析", r"选址", r"车辆路径",
        r"vrp", r"节点", r"边", r"图遍历",
    ],
    "simulation": [
        r"蒙特卡洛", r"仿真", r"排队论", r"多智能体", r"离散事件", r"系统仿真",
        r"agent", r"元胞自动机", r"随机模拟", r"仿真器",
    ],
}
ARCH_COMPILED = {a: [re.compile(p, re.IGNORECASE) for p in pats] for a, pats in ARCH_TRIGGERS.items()}


def norm_method(raw):
    """把一条原始方法名归一化为规范方法名列表（一条可能归一成多个）。"""
    s = raw.strip()
    hits = []
    for rx, norm in METHOD_PATTERNS:
        if rx.search(s):
            if norm not in hits:
                hits.append(norm)
    if not hits:
        for rx, norm in FALLBACK_METHOD_PATTERNS:
            if rx.search(s):
                hits.append(norm)
                break
    return hits


def load_briefs():
    cards = []
    for f in sorted(glob.glob(os.path.join(BRIEF_DIR, "*.json"))):
        data = json.load(open(f, encoding="utf-8"))
        for c in data:
            c["_source_file"] = os.path.basename(f)
            cards.append(c)
    return cards


def load_deeps():
    out = {}
    for f in sorted(glob.glob(os.path.join(DEEP_DIR, "*.json"))):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print("deep load fail", f, e, file=sys.stderr)
            continue
        out[d.get("paper_id", os.path.basename(f))] = d
    return out


def detect_archetypes(card):
    text_parts = []
    for k in ("title", "section_structure", "notes"):
        v = card.get(k)
        if v:
            text_parts.append(str(v))
    for k in ("task_types", "models_and_algorithms", "innovation_points", "figure_types"):
        v = card.get(k)
        if isinstance(v, list):
            text_parts.extend([str(x) for x in v])
    text = " ".join(text_parts)
    found = []
    for arch, rxlist in ARCH_COMPILED.items():
        for rx in rxlist:
            if rx.search(text):
                found.append(arch)
                break
    return found


def main_stats():
    briefs = load_briefs()
    deeps = load_deeps()
    n_brief = len(briefs)
    n_deep = len(deeps)

    # 方法频次
    method_papers = collections.defaultdict(set)   # norm -> set(paper_id)
    method_year = collections.defaultdict(lambda: collections.defaultdict(set))
    method_track = collections.defaultdict(lambda: collections.defaultdict(set))
    for c in briefs:
        pid = c.get("paper_id")
        year = c.get("year")
        track = c.get("track") or "X"
        for raw in (c.get("models_and_algorithms") or []):
            for norm in norm_method(str(raw)):
                method_papers[norm].add(pid)
                method_year[norm][year].add(pid)
                method_track[norm][f"{track}"].add(pid)

    method_freq = []
    for norm, pids in method_papers.items():
        n = len(pids)
        by_year = {str(y): len(s) for y, s in sorted(method_year[norm].items())}
        by_track = {t: len(s) for t, s in sorted(method_track[norm].items(), key=lambda kv: -len(kv[1]))}
        method_freq.append({
            "method": norm,
            "paper_count": n,
            "pct_of_corpus": round(n / n_brief, 4),
            "by_year": by_year,
            "by_track": by_track,
        })
    method_freq.sort(key=lambda x: -x["paper_count"])

    # 赛道×原型矩阵
    matrix = collections.defaultdict(lambda: collections.Counter())
    year_track_count = collections.Counter()
    for c in briefs:
        year = c.get("year")
        track = c.get("track") or "X"
        key = f"{year}_{track}"
        year_track_count[key] += 1
        for arch in detect_archetypes(c):
            matrix[key][arch] += 1

    matrix_rows = []
    for key in sorted(matrix.keys()):
        row = {"key": key, "year": int(key.split("_")[0]), "track": key.split("_")[1],
               "papers_in_cell": year_track_count[key]}
        for arch in ARCHETYPES:
            row[arch] = matrix[key].get(arch, 0)
        matrix_rows.append(row)

    # 验证手段覆盖率
    val_total = 0
    val_nonempty = 0
    val_tokens = collections.Counter()
    for c in briefs:
        val_total += 1
        vm = c.get("validation_methods") or []
        if vm:
            val_nonempty += 1
        for v in vm:
            s = str(v)
            for kw, tag in [("交叉验证", "交叉验证"), ("ROC", "ROC/AUC"), ("AUC", "ROC/AUC"),
                            ("对比", "与基线对比"), ("误差", "误差量化"), ("消融", "消融实验"),
                            ("灵敏度", "灵敏度分析"), ("鲁棒", "鲁棒性测试"), ("蒙特", "蒙特卡洛"),
                            ("复现", "算例复现"), ("对标", "外部对标")]:
                if kw in s:
                    val_tokens[tag] += 1
    val_coverage = round(val_nonempty / val_total, 4)

    # 图表类型统计
    fig_tokens = collections.Counter()
    for c in briefs:
        for f in (c.get("figure_types") or []):
            fig_tokens[str(f)] += 1
    fig_top = fig_tokens.most_common(30)

    # 创新点关键词聚类（简单词频）
    innov_counter = collections.Counter()
    stop = set("的了和与及在对为从把被而是之其于以有本我们提出通过模型方法问题本文".split())
    for c in briefs:
        for ip in (c.get("innovation_points") or []):
            for w in re.findall(r"[一-龥]{2,}", str(ip)):
                if w in stop or len(w) < 2:
                    continue
                innov_counter[w] += 1
    innov_top = innov_counter.most_common(40)

    # 页数分布
    pages = [c.get("page_count") for c in briefs if isinstance(c.get("page_count"), (int, float)) and c.get("page_count")]
    pages = [int(p) for p in pages]
    page_stats = {
        "n_with_pages": len(pages),
        "min": min(pages) if pages else None,
        "max": max(pages) if pages else None,
        "mean": round(sum(pages) / len(pages), 1) if pages else None,
        "median": sorted(pages)[len(pages) // 2] if pages else None,
        "buckets": {"<10": 0, "10-20": 0, "20-40": 0, "40-60": 0, ">60": 0},
    }
    for p in pages:
        if p < 10:
            page_stats["buckets"]["<10"] += 1
        elif p < 20:
            page_stats["buckets"]["10-20"] += 1
        elif p < 40:
            page_stats["buckets"]["20-40"] += 1
        elif p < 60:
            page_stats["buckets"]["40-60"] += 1
        else:
            page_stats["buckets"][">60"] += 1

    # 数据模态
    modality = collections.Counter(c.get("data_modality") or "未知" for c in briefs)
    # 奖级
    award = collections.Counter(c.get("award_level") or "未知" for c in briefs)

    # 写出 JSON
    method_out = {
        "generated_by": "scripts/corpus_cards.py --stats",
        "total_brief_cards": n_brief,
        "total_deep_cards": n_deep,
        "synonym_normalization_note": "models_and_algorithms 原始标签经 METHOD_SYNONYMS 正则归一；一条原始标签可命中多个规范方法名。",
        "methods": method_freq,
        "validation": {
            "coverage": val_coverage,
            "nonempty": val_nonempty,
            "total": val_total,
            "token_counts": dict(val_tokens.most_common()),
        },
        "figure_types_top": fig_top,
        "innovation_keywords_top": innov_top,
        "page_distribution": page_stats,
        "data_modality": dict(modality),
        "award_level": dict(award),
    }
    with open(os.path.join(ROOT, "corpus", "method_frequency.json"), "w", encoding="utf-8") as f:
        json.dump(method_out, f, ensure_ascii=False, indent=2)

    matrix_out = {
        "generated_by": "scripts/corpus_cards.py --stats",
        "archetypes": ARCHETYPES,
        "note": "行=年_赛道（track=X 表示早年未分题或无法识别赛道）；列=8大原型；值=该年该赛道下被关键词规则标注为该原型的论文数（一篇可同时命中多个原型）。",
        "rows": matrix_rows,
    }
    with open(os.path.join(ROOT, "corpus", "track_archetype_matrix.json"), "w", encoding="utf-8") as f:
        json.dump(matrix_out, f, ensure_ascii=False, indent=2)

    # ---- AGGREGATE_STATS.md ----
    lines = []
    A = lines.append
    A("# 华为杯语料聚合统计（Wave2A 任务一）")
    A("")
    A("> 全部数字由 `python scripts/corpus_cards.py --stats` 从 729 张简卡 + 80 张深卡现算，可重算。")
    A("> 口径：方法频次基于 `models_and_algorithms` 字段正则同义词归一；原型归属基于标题/任务/算法/创新点关键词规则，一篇论文可同时命中多个原型。")
    A("")
    A(f"- 简卡总数：**{n_brief}**（2004–2024，21 个年文件）")
    A(f"- 深卡总数：**{n_deep}**")
    A(f"- 写出显式验证手段的论文：**{val_nonempty}/{val_total} = {val_coverage*100:.1f}%**")
    A(f"- 页数：n={page_stats['n_with_pages']}, 均值 {page_stats['mean']}, 中位数 {page_stats['median']}, 区间 [{page_stats['min']}, {page_stats['max']}]")
    A("")
    A("## 一、方法频次 Top30（归一化后）")
    A("")
    A("| 排名 | 规范方法名 | 出现篇数 | 占比 | 主要年份分布 |")
    A("|---|---|---|---|---|")
    for i, m in enumerate(method_freq[:30], 1):
        top_years = sorted(m["by_year"].items(), key=lambda kv: -kv[1])[:4]
        ys = ", ".join(f"{y}:{n}" for y, n in top_years)
        A(f"| {i} | {m['method']} | {m['paper_count']} | {m['pct_of_corpus']*100:.1f}% | {ys} |")
    A("")
    A("## 二、原型分布（按年×赛道命中篇数）")
    A("")
    A("> 仅列 2022–2025 行；全量见 `corpus/track_archetype_matrix.json`。")
    A("")
    header = "| 年_赛道 | 论文数 | " + " | ".join(ARCHETYPES) + " |"
    A(header)
    A("|" + "---|" * (len(ARCHETYPES) + 2))
    for row in matrix_rows:
        if row["year"] >= 2022:
            cells = [str(row["year"]), row["track"], str(row["papers_in_cell"])]
            cells += [str(row[a]) for a in ARCHETYPES]
            # 重排为 key / papers / archs
            A(f"| {row['year']}_{row['track']} | {row['papers_in_cell']} | " + " | ".join(str(row[a]) for a in ARCHETYPES) + " |")
    A("")
    A("## 三、验证手段覆盖趋势")
    A("")
    A(f"- 全语料显式验证覆盖率：{val_coverage*100:.1f}%。")
    A("- 验证手段关键词计数：")
    for tag, cnt in val_tokens.most_common():
        A(f"  - {tag}: {cnt}")
    A("")
    A("## 四、图表类型 Top15")
    A("")
    for name, cnt in fig_top[:15]:
        A(f"- {name}: {cnt}")
    A("")
    A("## 五、创新点高频词 Top20（粗聚类）")
    A("")
    for w, cnt in innov_top[:20]:
        A(f"- {w}: {cnt}")
    A("")
    A("## 六、各年赛道主题速查表（从简卡标题聚合）")
    A("")
    by_year = collections.defaultdict(lambda: collections.defaultdict(list))
    for c in briefs:
        by_year[c.get("year")][c.get("track") or "X"].append(c.get("title", ""))
    for year in sorted(by_year.keys()):
        A(f"### {year} 年")
        for track in sorted(by_year[year].keys()):
            titles = by_year[year][track]
            sample = "；".join(titles[:3])
            A(f"- **{track}**（{len(titles)} 篇）：{sample}")
        A("")
    A("## 七、数据模态与奖级分布")
    A("")
    A("**数据模态**：")
    for k, v in modality.most_common():
        A(f"- {k}: {v}")
    A("")
    A("**奖级**：")
    for k, v in award.most_common():
        A(f"- {k}: {v}")
    A("")
    A("## 八、已知局限")
    A("- 方法归一化靠正则，长句/括号嵌套可能漏命中；未命中方法落入兜底桶（如“优化方法”），不进入 Top30 主榜。")
    A("- “禁忌搜索(TS)”61 篇中约 60 篇实际来自 Wave1 通用标签“禁忌搜索/启发式”，并非真禁忌搜索实现，读数时需打折；真正的 TS 实现偏少。")
    A("- 原型归属是关键词启发式，不是人工标注；同一篇可命中多原型，跨原型方法（如遗传算法同时服务优化与预测）属正常。")
    A("- 2014 与 2015 年赛道主题在简卡中完全雷同（A 水面舰艇防空/B 数据多流形/C 无线信道指纹/D 列车优化/E 数控机床/F 旅游路线），疑似 Wave1 年份/赛道标签串号；早年赛道速查表对 2015 年应谨慎使用。")
    A("- 2025 年无获奖论文简卡，语料中 2025 仅商业思路（C 级）。")
    A("- 早年（2004–2012）track 多为 X/空，赛道字母不可靠。")
    A("- 奖级“待确认”615/729，仅 114 篇明确一等；按奖级做统计时样本受限。")

    out_md = os.path.join(ROOT, "corpus", "cards", "AGGREGATE_STATS.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 控制台摘要
    print(f"[OK] briefs={n_brief} deeps={n_deep} methods={len(method_freq)}")
    print(f"[OK] method_frequency.json, track_archetype_matrix.json, AGGREGATE_STATS.md written")
    print("Top10 methods:")
    for m in method_freq[:10]:
        print(f"  {m['method']}: {m['paper_count']} ({m['pct_of_corpus']*100:.1f}%)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    if args.stats:
        main_stats()
    else:
        print(__doc__)
