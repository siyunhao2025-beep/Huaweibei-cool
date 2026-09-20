# CHANGELOG.md

## v0.2.0 — 2026-09-20（Wave4 真机验证 + 盲检扩容 + 奖级对账 + 品牌定稿）

### 品牌与隐私
- 品牌由旧名全量替换为 **「AI 作战中枢」**，新增 `docs/banner.png` 横幅并嵌入 README；README 重写为新品牌文案，免责语保留。
- 全量隐私清洗：面向用户文件零真实身份信息（姓名/拼音/导师/院校/课题组均零命中）；两个原始库存 JSON 中残留的第三方广告联系方式（广告微信号/ID，各 57 处）改写为「广告联系方式已剔除」。
- `docs/HANDOFF.md`（清洗版交接包）入库。

### MATLAB 真机验证（Wave4-A）
- MATLAB **R2024b 实测通过**：检出 113 个工具箱，Optimization / Global Optimization / Statistics and Machine Learning / Signal Processing / Image Processing 均 available（Deep Learning 未实测）。
- 求解器真机跑通并核对预期结果：`linprog` / `intlinprog` / `fmincon` / `ga` / `ode45`；`.mat` / `.csv` 与 Python 双向回读一致；Microsoft YaHei 中文出图无方块。
- 新增 `scripts/matlab_smoke.m` + `tests/test_matlab_smoke.py`（默认 SKIP，需 `HUAWEI_RUN_MATLAB=1` 才跑）+ `tests/fixtures/matlab_smoke_R2024b.log`；`modules/matlab-conventions.md` 改为实测版。

### 模板与工程（Wave4-B）
- 删除 `example.tex` 中引用不存在图片的装饰性二维码图块（loglo.png 缺陷）；干净目录 xelatex 双遍编译成功，产出 12 页 PDF，无需任何占位图。
- `audit_paper.py` 跑通；**Word 链路真机烟雾全跑通**（python-docx + audit_docx + `render_word.vbs` 导出 8 页 PDF，本机 Word 16.0）。

### 判型与盲检（Wave4-C）
- 盲检 golden set 由 10 题扩到 **30 题**（8 原型全覆盖，含 3 已知陷阱）。
- `match_rules.json` 调优：修 Markov→mechanism 误判 bug、补 evaluation 触发词、治"仿真验证"误触发；命中率 **93% → 97%（29/30）**，已知陷阱 3/3 = 100%。
- `tests/test_playbook_blind.py`（32 passed, 1 xfailed，阈值 90%）；`docs/DISTILLATION_METHOD.md` 新增盲检记录。
- P1：2023 A/B 档案补强；2024 A 扫描版思路走 OCR。

### 语料与数据（Wave4-D）
- 奖级口径对账统一：查清 615 vs 722 根因（两奖级存储分叉：索引 7/722 vs 卡片 114/615）。
- 729 篇自述式奖级文本扫描（防 2023C 评审题误判）：1 篇一等奖（2004）+ 12 篇数模之星提名奖（2021 专集目录）+ 716 待确认；`papers_index.json/csv` 合并式更新，新增 `award_evidence` 列。
- 禁忌搜索标签清洗 **61 → 4**（仅 4 篇真用，57 篇改标"启发式优化"）；同义词表收紧（排除 tabular_CPD 误匹配）。
- 12 篇早期论文低质量标题合并式重提；统计重算。

### tracks
- 2023 A/B 档案补强；2024 A 扫描版思路 OCR。

## v0.1.1 — 2026-09-20（交付复核修复）

- **广告清洗**：`papers_index.json/csv` 中 81 条被"加微 anjia"水印污染的标题已剔除（置为"待确认"并在 notes 记录）；`corpus_build.py` 标题提取增加广告行过滤、广告正则补充"有偿/代写/代充"，重跑索引不会再污染。
- **深卡修复**：2 张 deep 卡 schema 违例无损修复（`page_locations` 转对象、`independent_validation_design` 转字符串）；schema 测试取消豁免清单，729 简卡 + 80 深卡全部零违例。
- **skill 名称对齐**：SKILL.md frontmatter `name` 改为 `huawei-mcm`，与已安装的 junction 目录名一致。
- 全量 25 测试通过。

## v0.1.0 — 2026-09-20（Wave0–Wave2B 初始版本）

### Wave0：仓库骨架 + 全量抽文
- 仓库骨架、目录结构、`.gitignore`、LICENSE、README。
- 729 篇获奖论文全量抽文（`corpus_build.py`）。
- 论文模板与论文链脚本移植自 v2.1（`docs/UPSTREAM.md`）。
- 3 个骨架模块：solving / figures-interface / validation。
- vendored `skills/academic-figure/`。

### Wave1：729 简卡 + 80 深卡 + 赛题解析
- `corpus/cards/brief/` 729 简卡、`deep/` 80 深卡。
- `AGGREGATE_STATS.md`、`S3_star_patterns.md`、`S4_recent_trends.md`。
- `corpus/problem_analysis/`：innovation_algorithms / ai_prompts_distilled / CODE_INVENTORY。

### Wave2A：8 原型 playbooks + 24 题赛道档案 + 聚合统计
- `playbooks/`：8 原型 51 方法卡 + INDEX + match_rules.json。
- `tracks/`：2022–2025 共 24 题档案 + README + track-selection-stats。
- `method_frequency.json` / `track_archetype_matrix.json`。

### Wave2B：模块全集 + 评分量表 + 新脚本 + 文档全集（本次）
- `modules/` 20 个任务契约模块（充实 solving/validation/figures-interface，新增 17 个）。
- `docs/SCORING_RUBRIC.md`：四维度评分量表 + 自评清单 + 官方来源标注（经验推断声明）。
- 新脚本：`playbook_match.py` / `evidence.py` / `progress.py` / `review.py` / `submission_audit.py`（+ 辅助 `blind_check.py`），均 `--help` 通过。
- 留出盲检 10 篇（4/10 对齐，失败案例如实记录于 `DISTILLATION_METHOD.md`）。
- `docs/`：DISTILLATION_METHOD / PHASE_GATES / ACCEPTANCE / ARCHITECTURE / PEER_COMPARISON / CHANGELOG。
- 充实 `SKILL.md`：移除骨架标记，模块路由扩为 20，补充 AI 披露硬规则与新脚本索引。
