# 华为杯研赛 Playbook 总索引（Wave2A）

> 数据基础：729 张获奖论文简卡（2004–2024）+ 80 张深卡 + 2022–2025 赛题解析。
> 所有方法卡均从卡片数据蒸馏，案例定位指向真实 paper_id。
> 证据等级：A=深卡支持；B=简卡支持；C=商业资料/推断。

## 八原型一览

| # | 原型目录 | 触发核心 | 方法卡数 | 代表深卡 |
|---|---|---|---|---|
| 1 | [optimization](optimization/00_overview.md) | 约束下求极值（排样/调度/选址/分配） | 7 | 2022_D Gurobi、2024_A RL |
| 2 | [evaluation](evaluation/00_overview.md) | 多指标打分排序选优 | 6 | 2024_D 熵值法三层次 |
| 3 | [prediction](prediction/00_overview.md) | 外推未来/未知量 | 7 | 2022_E LSTM-FC |
| 4 | [classification-cv](classification-cv/00_overview.md) | 分类/识别/检测/分割 | 7 | 2024_E YOLO+DeepSORT |
| 5 | [mechanism](mechanism/00_overview.md) | 第一性原理方程建模 | 6 | 2021_C HH 神经元 |
| 6 | [signal](signal/00_overview.md) | 信号谱估计/滤波/超分辨 | 6 | 2022_A FMCW-MUSIC |
| 7 | [spatial-graph](spatial-graph/00_overview.md) | 空间/图/网络/路径 | 6 | 2024_D Kriging/GWR |
| 8 | [simulation](simulation/00_overview.md) | 随机仿真/排队/多智能体 | 6 | 2024_F Ogata thinning |

## 跨原型方法说明

一个方法常服务多个原型，本索引按"主原型"归档，跨原型使用见各卡"相邻方法辨析"：

- **遗传算法/PSO/SA**：主归 optimization；也用于 prediction（调 ML 超参）、spatial-graph（布局优化）。
- **随机森林/XGBoost**：主归 prediction；也用于 classification-cv（分类）、evaluation（特征重要性）。
- **LSTM/GRU**：主归 prediction；也用于 classification-cv（时序分类）。
- **聚类（K-means/DBSCAN/GMM）**：主归 classification-cv（无监督分组）；也用于 evaluation（指标分组）、spatial-graph（空间聚类）。
- **PCA**：主归 evaluation（降维评价）；也用于 classification-cv（特征工程）。
- **微分方程/机理**：主归 mechanism；与 prediction 混合为"物理+ML 残差"。
- **排队论/蒙特卡洛**：主归 simulation；也用于 optimization（服务能力规划）。
- **压缩感知**：主归 signal；也用于 spatial-graph（稀疏存储）。

## 使用建议

1. 先按题面用 [match_rules.json](match_rules.json) 匹配原型。
2. 进对应原型 `00_overview.md` 看分布与骨架。
3. 按方法卡"触发判据"选具体方法，看 baseline→改进链。
4. 用"华为杯真题案例定位"回查深卡页码。
5. 注意：2024 高分趋势是"物理机理打底 + ML 学残差 + 消融/对标验证"，纯遗传/纯熵权/纯 ARIMA 单独已降温。

## 已知局限

- 方法卡证据以 2024 年深卡最厚（30 篇集中在 2024），早年深卡偏少。
- 部分原型（simulation 的蒙特卡洛、mechanism 的微分博弈）深卡仅 1-2 篇，证据等级标 A 但样本小。
- 2025 年无获奖论文简卡，方法卡不引用 2025 真题案例。
