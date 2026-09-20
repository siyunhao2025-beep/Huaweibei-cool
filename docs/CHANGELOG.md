# CHANGELOG.md

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
