# docs/DISTILLATION_METHOD.md · 蒸馏方法论

> 本文件说明 Huaweibei-cool 知识库是怎么从 729 篇论文蒸馏出来的、证据怎么分级、纪律是什么、留出盲检验证过没有、还有哪些已知局限。

## 1. 语料覆盖率

- **简卡 729 张**：2004–2024 共 21 个年文件，位于 `corpus/cards/brief/{年}.json`。
- **深卡 80 张**：位于 `corpus/cards/deep/{paper_id}.json`，含逐问方法链、抽象拆解、高分理由等富字段。
- **赛道档案**：2022–2025 共 24 题（`tracks/`），2025 全部为 C 级商业思路。
- **方法卡**：8 原型 51 张（`playbooks/`）。
- **专项统计**：`AGGREGATE_STATS.md`、`S3_star_patterns.md`（2021 数模之星 12 篇）、`S4_recent_trends.md`（2022–2024 共 125 篇）。

## 2. 卡片 schema

- **简卡字段**：paper_id/year/track/title/award_level/task_types/models_and_algorithms/data_modality/data_scale/validation_methods/figure_count/figure_types/innovation_points/page_count/section_structure/source_locations/confidence。
- **深卡额外字段**：per_question_method_chain/objective_function/abstract_deconstruction/judge_high_score_reasons/independent_validation_design/sensitivity_robustness_ablation 等。
- 卡片由 `scripts/corpus_cards.py` 生成；schema 与统计可重算。

## 3. 证据等级定义（A/B/C）

- **A**：深卡支持（逐问方法链+页码+高分理由）。
- **B**：简卡支持（models_and_algorithms 字段）。
- **C**：商业/自媒体思路或推断（如 2025 赛题解析、创新算法包）。

playbook 每卡在头部标注证据等级；赛道档案按 A/B/C 标注可信度。

## 4. 蒸馏纪律

- **单次事件不升级为定律**：某方法某年好用，不等于普适；只有多次复现才写进通则。
- **关键词统计可重算**：所有数字来自 `corpus_cards.py --stats`，不手填。
- **奖级待确认不滥用**：729 篇中仅 114 篇明确一等，615 篇"待确认"，不按奖级做强结论。
- **原型归属是启发式**：一篇可命中多原型，不做互斥分类。

## 5. 留出盲检（2026-09-20）

### 方法

从 2023 年简卡（58 篇）中排除已入深卡的 1 篇，跨赛道分层取 10 篇未参与深卡提炼的论文，以"标题+task_types+models"作题面跑 `scripts/playbook_match.py`，比较匹配原型与 task_types 粗推原型。

### 结果：对齐 4/10 = 40%

| paper_id | 匹配原型 | 置信 | task_types推 | 一致 | 题面 |
|---|---|---|---|---|---|
| 2023_A_A23100070049 | simulation | 0.80 | mechanism | N | WLAN 信道接入建模 |
| 2023_A_A23102470073 | simulation | 0.80 | mechanism | N | WLAN 信道接入建模 |
| 2023_B_B23100070010 | optimization | 0.85 | optimization | Y | DFT 整数分解 |
| 2023_B_B23100070173 | optimization | 0.65 | unknown | N | DFT 整数分解 |
| 2023_C_C23102540029 | optimization | 0.85 | evaluation | N | 竞赛评审方案 |
| 2023_C_C23102890004 | unknown | 0.00 | unknown | Y | 竞赛评审方案 |
| 2023_D_D23100060041 | prediction | 0.85 | prediction | Y | 双碳影响因素 |
| 2023_D_D23102690008 | prediction | 0.85 | prediction | Y | 双碳路径规划 |
| 2023_E_E23100650012 | classification-cv | 0.90 | prediction | N | 脑卒中诊疗 |
| 2023_E_E23102550019 | classification-cv | 0.90 | prediction | N | 脑卒中诊疗 |

### 失败案例与归因（如实记录）

1. **"仿真验证"过度触发 simulation（A 题 WLAN，2 例）**：WLAN Bianchi/Markov 链本质是机理/解析建模，但 task_types 含"仿真验证"命中 R08，被判 simulation。根因：match_rules 缺"Markov 链/通信协议/信道"这类机理触发词。**结论：关键词粗筛对"用仿真做验证的解析题"会误判**，需人工复核。
2. **跨原型题天然歧义（E 题脑卒中，2 例）**：脑卒中诊疗同时含"分类/亚型"与"预测/预后"，匹配到 classification-cv 是合理成员之一，但 task_types 期望 prediction。**这不是匹配错，是题本身跨原型**——印证"主+辅原型"设计。
3. **评价题误判为优化（C 题评审，1 例）**：`方案/评审` 词未强触发 evaluation，反而被 optimization 词命中。**评价类题需补"评审/方案比较"触发词**。
4. **unknown 是真空白（C 题 1 例）**：题面无任何规则关键词，正确地返回 unknown 人工判断。
5. **"unknown=unknown"算一致属虚高**：4/10 里有 1 条是双方都 unknown，真实"有效命中"约 3–4/9。

### 盲检结论

- playbook_match 对**信号明确的优化/预测题**（DFT 优化、双碳预测）命中可靠。
- 对**跨原型题、含"仿真验证"字样的解析题、纯评价题**会误判或漏判。
- 这与 `problem-typing.md` 的定位一致：**脚本只做粗筛建议，人工复核不可省**。未夸大命中率。

## 6. 已知局限

- **奖级待确认比例高**：615/729 未确认奖级，按奖级统计受限。
- **乱码论文**：早年部分 PDF 抽文乱码（如 2017 C 题标题乱码），卡片质量打折。
- **早期论文摘要不规范**：2004–2012 摘要多为流水账，S3 模板主要靠 2021 星队。
- **2025 仅商业资料**：无获奖论文简卡，方法卡不引用 2025 真题。
- **2014/2015 赛道标签疑似串号**（AGGREGATE_STATS §八）。
- **深卡年份偏斜**：80 深卡集中在 2021/2024，早年深卡少。
- **原型归属是关键词启发**，非人工标注。
