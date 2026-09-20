# modules/training.md · 赛前训练计划

> **目标**：赛前把"方法体系 + 选题手感 + 模拟赛"练到位，比赛日不慌。本模块基于 729 篇语料的方法统计与代表论文，**是基于语料的建议，非强制**。

## 1. 方法体系搭建（按原型过一遍）

按 8 原型把 `playbooks/` 的方法卡各挑 1–2 个练到能跑：

| 原型 | 赛前至少练熟 | 语料高频证据 |
|---|---|---|
| optimization | MILP(intlinprog/Gurobi)、GA/NSGA-II 框架 | GA 82 篇、整数规划 49 篇 |
| evaluation | AHP+熵权+TOPSIS 组合拳 | AHP 28 篇、熵权/TOPSIS 高频 |
| prediction | ARIMA 基线 + 树模型(XGB/RF)/LSTM | RF 42、ARIMA 33、LSTM 32 |
| classification-cv | 分类基线 + 聚类(K-means/FCM) | 聚类 91、SVM 46 |
| mechanism | 微分方程(ode45) + 一个机理模型 | 微分方程 48 |
| signal | FFT/滤波/谱估计 | 滤波 30、小波 30 |
| spatial-graph | 最短路/VRP/网络流 | 图论 54 |
| simulation | 蒙特卡洛/离散事件 | — |

> 方法频次来自 `corpus/cards/AGGREGATE_STATS.md` Top30。

## 2. 按原型刷题（代表论文清单思路）

- 不熟哪个原型，就从 `corpus/cards/deep/` 挑该原型的深卡精读：
  - optimization：2022_D PISA(Gurobi)、2024_A RL。
  - evaluation：2024_D 熵值法三层次。
  - prediction：2022_E LSTM-FC。
  - classification-cv：2024_E YOLO+DeepSORT。
  - mechanism：2021_C HH 神经元。
  - signal：2022_A FMCW-MUSIC。
  - spatial-graph：2024_D Kriging/GWR。
  - simulation：2024_F Ogata thinning。
- 每篇精读：它的模型链、验证手段、创新点怎么写的。

## 3. 模拟赛安排

- **至少 1 次完整 72h 模拟**：按 `workflow.md` 时间线跑一遍往届真题，走完 P0–P6。
- 模拟赛重点练：选题速度（中午前定）、边做边写、验证同步。
- 模拟后按 `distillation.md` 复盘。

## 4. 团队分工建议

- **建模手**：主责 P2/P3 建模与算法。
- **代码手**：主责 P3 求解、落盘、复现（MATLAB/Python）。
- **写作手**：主责 P4/P5 论文与打磨，边做边记。
- 三人都要懂全流程，避免单点依赖；赛前约定谁备份谁。

## 5. 工具与环境赛前就绪

- [ ] Python 环境与 MATLAB 都能跑。
- [ ] 论文模板（LaTeX/Word）赛前编译过一遍。
- [ ] 出图中文不方块。
- [ ] 常用求解器/库版本固定，赛中不临时装。

## 6. 趋势提醒（练什么更值得）

- 升温：随机森林/XGBoost、物理+ML 混合、消融验证。
- 降温：纯遗传、纯熵权、纯 ARIMA 单独使用。
- 赛前别只练降温方法；组合与混合是重点。

## 7. 边界

- 以上是基于语料统计的训练建议，不是官方要求。
- 刷题贵精不贵多，吃透 3–5 篇深卡胜过泛读 20 篇。
