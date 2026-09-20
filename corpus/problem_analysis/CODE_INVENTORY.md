# 代码资产静态盘点（py / m / ipynb）

> 盘点方式：Python 静态扫描（`_work/s5_codescan.py`），**不运行代码**。提取 import、def、MATLAB 求解器调用、算法关键词。
> 证据等级：**C（商业资料，仅供参考）**。
> 总览：扫描 **246 个代码文件** = Python 113 + MATLAB 122 + Jupyter 11。
> **MATLAB 标注**：用户主力为 MATLAB，下文 .m 文件特别标注。

## 一、按年/题/语言统计

| 年 | 题 | py | m | ipynb | 主要算法关键词（静态命中） |
|---|---|---|---|---|---|
| 2022 | E | 0 | 3 | 4 | LogisticRegression/RandomForest/xgboost/lightgbm/LSTM/tensorflow/keras/sklearn |
| 2022 | F | 0 | 3 | 2 | kmeans（聚类） |
| 2022 | A/B/C/D | 0 | 0 | 0 | 代码在 zip/rar 内（未解压） |
| 2023 | C/D/E/F | 0 | 0 | 0 | 仅思路 PDF + mp4，无散代码 |
| 2024 | A | 0 | 2 | 0 | **ga 遗传算法** |
| 2024 | B/C/D/E/F | 0 | 0 | 0 | 代码在 zip 内（未解压） |
| 2025 | B | 3 | 0 | 0 | fft、ga、PCA、RandomForest、sklearn、ols |
| 2025 | C | 0 | 4 | 0 | **aco、ga、pca、fft、gray、ols**（MATLAB） |
| 2025 | E | 0 | 0 | 5 | fft/welch/hilbert、LR/RF/SVC/MLM/PCA、domain 迁移、DEA |
| 2025 | X（创新算法包） | 110 | 110 | 0 | 全算法库：ga/fmincon/pso/intlinprog/linprog/nsga/AHP/TOPSIS/DEA/arima/gray/dijkstra/floyd/networkx/kmeans/pca/feedforwardnet/ode45 |

## 二、MATLAB 资产（用户主力，重点）

### 2022 E 题（3 个 .m）
- 机器学习路线：LogisticRegression/RandomForest/xgboost/lightgbm/LSTM（Python 库名出现在 .m 注释或混写，待确认）。

### 2022 F 题（3 个 .m）
- kmeans 聚类（选址/分组）。

### 2024 A 题（2 个 .m）
- **ga 遗传算法**求解（优化类）。

### 2025 C 题（4 个 .m）
- **aco 蚁群、ga 遗传、pca、fft、gray 灰色、ols 回归**——覆盖优化+统计+图论。

### 2025 创新算法包（110 个 .m）
- 与 Python 版一一对应（每算法 .m + .py）。MATLAB 求解器命中：**fmincon、ga、intlinprog、linprog、lsqnonlin、kmeans、pca、feedforwardnet、ode45、mapminmax**。
- 覆盖：优化（GA/PSO/ACO/SA/NSGA/intlinprog）、评价（AHP/TOPSIS/DEA/熵权/模糊综合）、预测（ARIMA/灰色/回归/插值）、图论（Dijkstra/Floyd）、机器学习（聚类/PCA/神经网络 feedforwardnet）。

## 三、Python 资产

### 2025 B 题（3 个 .py）
- numpy/pandas/sklearn：fft 频谱、ga 优化、PCA 降维、RandomForest 分类、ols 回归。

### 2025 E 题（5 个 .ipynb）
- 轴承故障诊断：welch/hilbert 信号处理 + LR/RF/SVC/MLP 分类 + PCA 降维 + domain 迁移学习 + DEA 评价。

### 2025 创新算法包（110 个 .py）
- 与 .m 对应，依赖：numpy/pandas/scipy/sklearn/matplotlib。
- 算法：优化（scipy.optimize/curve_fit/differential_evolution/ga/pso/aco/intlinprog/linprog/nsga）、统计（arima/gray/ols/ridge）、图论（networkx/dijkstra/floyd）、ML（KMeans/RandomForest/PCA/MLP/keras/LSTM）、评价（AHP/TOPSIS/DEA/熵权/模糊综合）。

## 四、未解压代码（zip/rar）

- 2022 A/B/C/D 题代码、2024 A 题 4 zip+1 rar、2024 C 题 3 zip——**均在压缩包内，本次未解压**。
- 解压规则：zip 用 Expand-Archive；**rar 需 7-Zip/WinRAR（Expand-Archive 不支持），标注「需手动解压」**。
- Wave2 如需某题可运行代码，按题单包解压到仓库 `_work/temp_unzip/`。

## 五、静态盘点局限

- 仅提取 import/函数名/求解器调用，**未运行、未验证可执行性**。
- 部分 .m 文件命中 Python 库名（如 sklearn）可能为注释或混写，已标注待确认。
- 算法关键词词典见 `_work/s5_codescan.py`（KW 字典）。

## 六、来源

- 原始扫描：`corpus/problem_analysis/_code_scan.json`（246 条记录）
- 汇总脚本：`_work/s5_codescan.py`、`_work/s5_codesum.py`
