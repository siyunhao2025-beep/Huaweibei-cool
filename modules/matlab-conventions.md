# modules/matlab-conventions.md · MATLAB 工程规范

> **目标**：用户主力是 MATLAB，把"代码能跑、数字能对上、附录能复现"做成默认纪律。语料静态盘点见 `corpus/problem_analysis/CODE_INVENTORY.md`（扫 246 个代码文件，其中 MATLAB 122 个；另有压缩包内未解压的 .m）。
> 注意：agent 默认可执行求解链仍是 Python；MATLAB 作为"用户可运行求解器"一等公民。

## 1. 求解器资产速查（语料高频）

从 CODE_INVENTORY 静态命中的 MATLAB 求解器：

- 优化：`fmincon`、`ga`、`intlinprog`、`linprog`、`lsqnonlin`、`gamultiobj`(NSGA 类)。
- 统计/ML：`kmeans`、`pca`、`feedforwardnet`、`mapminmax`。
- 微分方程：`ode45`。
- 信号/其他：`fft`、`gray`(灰色)、`aco`/`ga`/`pso` 自定义。

> 这些是"语料里有人用过"，不是必须用；按题选。

## 2. 固定随机种子

- 每个含随机性的脚本开头固定 `rng(seed)`（及 GPU/统计工具箱对应种子）。
- 优化启发式（ga/particleswarm）也要设种子，否则结果不可复现。
- 论文里报的随机结果，必须用固定种子重跑过。

## 3. 结构化结果落盘

- 结果用 `.mat` 存关键变量，用 `.csv` 存表格结果，用 `.json` 存元信息。
- **禁止只 `disp` 到命令行**——D3 写论文时找不到数字。
- 落盘文件命名带问题号：`q1_baseline_metrics.mat`。
- 论文数字一律从落盘文件读，不从控制台截图。

## 4. 与论文数字一致性

- 跑一次求解→落盘→论文从落盘填数。
- 换 seed/换参数后重跑，落盘文件更新，论文同步改（见 `change-management.md`）。
- 附录代码里的参数/超参与正文一致。

## 5. 代码附录排版

- 附录放完整可复现代码，注明 MATLAB 版本、依赖工具箱。
- 关键行注释"为什么这么写"，但不堆废话。
- AI 辅助写的程序，开头按 2026 规定加注释："本程序及代码是在人工智能工具辅助下完成的"，标工具名/版本/机构/发布日期。

## 6. 与 Python 互操作

- agent 默认链用 Python（numpy/pandas/scipy/sklearn）。
- MATLAB↔Python 数据交换：用 `.mat`（`save`/`load`）或 `.csv` 做中间格式，不直接内存传。
- 用户在 MATLAB 跑求解器出结果→落盘→Python 读结果做图/统计→回论文。
- 复杂 Python 库（sklearn 模型）若 MATLAB 没有等价物，在 Python 里跑，MATLAB 只做求解与出图。

## 7. 性能优化

- **向量化优先**：避免 for 循环逐元素，用矩阵运算。
- 大规模优化用 `ga`/`particleswarm` 并行（`'UseParallel',true`）或 parfor。
- 计时：`tic/toc`，大规模题在论文给运行时间/复杂度。
- 预分配数组，不动态增长。

## 8. 常见 MATLAB 坑

- 没固定种子，结果每次跑不一样，论文数字对不上。
- 路径含中文/空格导致读不到文件。
- 图不导出矢量，位图糊；中文标题方块（要设 `gca` 字体）。
- 把脚本当函数用，工作区变量污染。
- `intlinprog` 求解失败没检查退出标志就当成功。
