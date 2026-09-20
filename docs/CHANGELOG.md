# CHANGELOG.md

## v0.4.0 — 2026-09-21（Wave6 集成：优秀论文自检表全量固化 + 机检脚本 + P4/P6 门禁打通）

### 优秀论文自检表全量固化（Wave6-A 资产 + 机检脚本）
- 新增 `assets/checklists/paper_checklist.json`：**138 条结构化自检条目**（全局格式 F01–F06 / 篇幅 L01–L17 / 摘要 A01–A10 / 引言 B01–B15 / 总体分析 T01–T08 / 假设 H01–H06 / 符号 S01–S06 / 具体分析 C01–C08 / 模型准备 P01–P11 / 模型建立 M01–M14 / 模型求解 Q01–Q09 / 检验 V01–V07 + W01–W05 / 评价 E01–E08 / 改进 I01–I02 / 推广 G01–G02 / 参考文献 R01–R02 / 附录 X01–X02）。
- 新增 `assets/checklists/优秀论文自检表.md`：人读版，138 条逐章排版，AI 相关措辞已中性化（"AI 速成/claude"→"可用 AI 辅助起草、作者核验并按当届规定披露"）。
- 新增 `scripts/paper_checklist.py`：13 类可机检规则（图表宽度/全中文题注/引用闭合/三线表/优点>缺点/无加粗/检验章节/参考文献无 DOI 等），支持 `--mark ID=pass|na` 人工裁决持久化、`--strict` 存在未裁决人工条目即失败、sidecar JSON 输出。
- `scripts/contest_init.py`：初始化工作目录时自动复制自检表到 `论文/`。
- 新增 fixture `tests/fixtures/checklist_pass.tex`（合规，机检 0 ❌）与 `checklist_fail.tex`（埋错，机检全检出）；新增 `tests/test_paper_checklist.py` **7 项**（JSON 138 条可解析 / 人读版存在 / --help 退出 0 / pass fixture 0 fail / fail fixture 全检出 / --mark 持久化 + strict 门 / contest_init 复制自检表）。

### 模块内嵌与门禁打通（Wave6-B）
- `modules/paper-writing.md`：138 条自检表逐章内嵌，写完即勾；§6.1 逐条对照 `gmcmthesis.cls` 现状。
- `modules/abstract.md` 补 A01–A10；`modules/validation.md` 补 V01–V07 + W01–W05；`modules/figures-interface.md` 补 Q02/Q03/Q06/Q07/Q08/T06；`modules/polishing.md` 终审接入 paper_checklist 闭环；`modules/submission.md` P6 硬退出条件。
- 门禁：`docs/PHASE_GATES.md`（P4/P6）、`docs/ACCEPTANCE.md`（§8 自检表验收）、`modules/phases.md`（P4/P6）、`scripts/progress.py`（P4 查自检表文件存在；P6 查已勾选表 + sidecar 未裁决计数）。
- `tests/test_progress_gate.py` 新增 **6 项**正反例（P4 无表 FAIL / 有表 PASS；P6 无勾选表 FAIL / sidecar 缺失 FAIL / sidecar 含未裁决 FAIL / 勾选表+干净 sidecar PASS）。

### ⚠ 已知冲突：F03 二三级标题字体（以官方规范为准）
- 第三方自检表 F03 要求"二三级标题小四号**黑体**"；但华为杯官方 `华为杯_论文章节规范.md` §2.3(1) 明确为"小四号**宋体**"，且禁止改 `gmcmthesis.cls`；`gmcmthesis.cls` 与 Word 模板现状均为宋体小四。
- Wave6-B 未改模板，在 `modules/paper-writing.md` §6.1 如实标注冲突、**以官方宋体为准**，待用户最终裁决。本仓库不擅自改模板。

### 3 处转录存疑已经用户确认定稿（2026-09-21）
- 原转录 M14 / V05 / I02 三处存疑，经用户确认后定稿：M14=预测模型评估（讲如何控制输出，与 M11 同构）；I02=以整段写为主、可分点但不能跑题；V05=误差检验优先使用五折交叉验证。
- `paper_checklist.json` 三条 notes 置 `null`，人读版/`paper-writing.md`/`validation.md` 去掉“待用户确认”标注；`test_paper_checklist.py` 断言同步改为 notes 为 null。

### 集成与发布（Wave6-C）
- 全量 pytest **87 passed / 2 skipped / 1 xfailed**（MATLAB skip、2017_B xfail）。
- doctor.py 本机 8 PASS / 1 WARN（graphviz dot 可选）/ 0 FAIL。
- paper_checklist 正反例实测：pass fixture ✅17 ❌0 退出 0；fail fixture 检出 8 ❌（H05/Q02/Q03/Q04/Q09/V04/E03/R02）退出 1。
- quickstart demo 全链路通，对 demo 玩具稿跑 paper_checklist 如实检出 1 ❌（V04 缺灵敏度，玩具稿非 100% 合规，不修）。
- 3 张路线图重渲染非空；新增 `paper_checklist.py --help` 退出 0；7 条关键脚本 --help 全 0。
- 隐私与品牌 grep：身份词/旧品牌/广告 ID 全零命中；华为杯面向用户的 `assets/checklists/` 与 `modules/` 无商业 AI 产品名残留（有单测强制）。

## v0.3.0 — 2026-09-20（Wave5 集成：技术路线图体系 + 对抗挑刺 + 工程化开箱 + 写作图表细节库）

### 技术路线图体系（Wave5-A）
- 新增 `modules/technical-roadmap.md`：论文图1（技术路线图）六层主链路 + 反馈回路 + 小问映射 + 章节回链规范。
- 新增 `assets/roadmap/roadmap.schema.json` + 8 原型 YAML 模板（optimization/evaluation/prediction/classification-cv/mechanism/signal/spatial-graph/simulation）。
- 新增 `scripts/render_roadmap.py`（YAML→PNG/PDF/MMD/DOT 四格式，无 CJK 字体自动切 `label_en` 英文回退）与 `scripts/audit_roadmap.py`（schema + 覆盖度 + 孤立节点 + 色盲安全色）。
- 新增 `docs/examples/roadmap/` 3 个完整样例（classification/mechanism/optimization），含 YAML + 渲染产物。
- 8 个 playbook `00_overview.md` 与 kickoff-audit/figures-interface/paper-writing/submission 四模块交叉引用技术路线图。
- 测试 `tests/test_roadmap.py` 12 项全绿。

### 对抗式挑刺修复（Wave5-B）
- 修复 `交付说明.md` 3 处悬空路径/计数/自相矛盾条目；`requirements.txt` 旧品牌词统一为「AI 作战中枢」；`CLAUDE.md` 与 `AGENTS.md` 字节级镜像。
- 7 份赛道档案裸"待确认"改写为"证据不足，待补充"（官方模板不在语料，不编造）。
- 确认 80 张深卡零违例、125 条 playbook 引用全部存在、P0–P6 门禁四处一致、数字全部可重算。
- 新增 `docs/REVIEW_v0.3.md` 完整评审记录。

### 工程化与开箱体验（Wave5-C）
- 新增 `scripts/doctor.py`：一键环境自检（Python/依赖/pytest/git 代理/xelatex+CJK/matplotlib CJK/MATLAB/Word COM/graphviz），`--json` 供测试断言。
- 新增 `docs/TROUBLESHOOTING.md`：环境/编译/字体常见坑与修复。
- 新增 `docs/examples/quickstart/` 玩具样例（题面+yaml+读题审计桩+tex+PDF+roadmap 图+README）+ `scripts/quickstart_demo.ps1` 一键全链路（contest_init→playbook_match→render_roadmap→xelatex）。
- 新增 `.github/workflows/ci.yml`：Ubuntu + Python 3.12，跑 doctor（continue-on-error）+ pytest；MATLAB 用例默认 skip。
- `requirements.txt` 补全 lxml/jsonschema/pyyaml/matplotlib 并加版本注释；`scripts/matlab_smoke.m` 加 Deep Learning license 探测块；`modules/matlab-conventions.md` DL 状态更新为 unavailable。
- 测试 `tests/test_doctor.py` 4 项全绿。

### 写作与图表细节库（Wave5-D）
- `modules/abstract.md` 扩 38 条句式库；`modules/deai-writing.md` 扩 18 组 AI 味对照；`modules/innovation.md` 扩四象限 25 案例；`modules/validation.md` 扩八原型验证菜单。
- 新增 `docs/FIGURE_COOKBOOK.md`：18 图种速查 + 八原型必备图清单 + 配色/字号/导出规范。
- 新增 `assets/scaffold/题目/读题审计报告模板.md`（7 节 + 示范填写）。

### 集成与发布（Wave5-E）
- 全量 pytest **74 passed / 2 skipped / 1 xfailed**；doctor 本机 8 PASS / 1 WARN；quickstart demo 全链路通；3 张路线图重渲染非空白；干净目录 xelatex+bibtex 双遍出 12 页 PDF。
- 隐私与品牌 grep：身份词/旧品牌词/广告 ID 全部零命中（含 untracked 新文件）。
- `.gitignore` 加例外允许 `docs/examples/` 下演示 PDF 入库；SKILL.md/README 补新文件索引。
- 修复集成期发现的品牌词残留（doctor.py 3 处、ci.yml 1 处、REVIEW_v0.3.md 1 处、contest.schema.json 1 处）、technical-roadmap.md "三种产物"→"四种产物"、CI doctor 步骤 continue-on-error。

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
