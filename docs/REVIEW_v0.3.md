# docs/REVIEW_v0.3.md · Wave5-B 对抗式挑刺与修复记录

> 视角：严苛国一评委 + 挑剔开源用户。基线 commit `9731960`（v0.2.0）。
> 本文件只记录 Wave5-B 的发现与处置；并行分片（A/C/D）正在改的文件只登记不改动。
> 生成时间：2026-09-20。

## 0. 基线与验证环境

- Python 3.14.7；`python scripts/corpus_cards.py --stats` 实算：**briefs=729, deeps=80, methods=67**。
- 全量测试 `python -m pytest tests/ -q`：**74 passed, 2 skipped, 1 xfailed**（A/C/D 并行新增 doctor/roadmap 等测试后仍全绿；我未改任何测试）。
- 奖级实算（`corpus/papers_index.json`）：**一等奖 1 + 数模之星提名奖 12 + 待确认 716 = 729**，与文档口径一致。

---

## 一、已修复（问题描述 + 修复方式 + 验证结果）

### 1. 深卡 schema 违例（任务二）
- **问题**：任务书称 v0.2.0 遗留 2 张深卡违例（`2009_X_论文1042215B 最终`、`2022_C_C22103560098`）。
- **核实结论**：基线已修复，无需再改。手动用 `corpus/schemas/deep-card.schema.json` 对这两张逐字段校验，**均 VALID**；全量 80 张深卡 0 违例；`tests/test_card_schemas.py` 已**无任何豁免清单**（docstring 明确"不再保留豁免清单"），`test_deep_cards_all_valid` 硬断言 `len(files)==80` 且 `bad==[]`。
- **附带修复（文档自相矛盾）**：`交付说明.md` §4.2 第 2 条仍写"2 张深卡 schema 违例已知未改"，与同文件 §4.1"v0.1.1 已修复、本轮保持零违例"及测试全绿**直接矛盾**。已删除该条并把 §4.2 后续 8 条重新编号。
- **验证**：`pytest tests/test_card_schemas.py` 3 passed；脚本全量扫 80 张 invalid=0。

### 2. 交付说明悬空路径（任务一/四）
- **问题**：`交付说明.md` 第 156 行写"读 `docs/training.md`"，但 `docs/training.md` 不存在（训练模块实为 `modules/training.md`）。
- **修复**：改为 `modules/training.md`。
- **验证**：`Test-Path modules/training.md` = True。

### 3. 交付说明文档计数错误（任务四/五）
- **问题**：`交付说明.md` 写"9 份文档（docs/）"，实际 `git ls-files docs/*.md` = **10 份**（ACCEPTANCE/ARCHITECTURE/CHANGELOG/DISTILLATION_METHOD/HANDOFF/PEER_COMPARISON/PHASE_GATES/SCORING_RUBRIC/TRACK_ARCHIVE_2004_2021/UPSTREAM）。
- **修复**：改为"10 份文档"。

### 4. 旧品牌词残留（任务四）
- **问题**：`requirements.txt` 首行注释含旧内部品牌代号（已脱敏，不在此处复现字面），未统一为对外品牌名。
- **修复**：改为"华为杯研赛 **AI 作战中枢** 运行依赖"。
- **验证**：全仓旧品牌代号正则在用户可见文本文件**零命中**。

### 5. AGENTS.md / CLAUDE.md 镜像不一致（任务四）
- **问题**：两文件"同源镜像"，但 Compare-Object 显示第 15、21 行两处引号字形不同（`"反 AI"` vs `"反 AI"`），并非字节一致。
- **修复**：以 `AGENTS.md` 覆盖 `CLAUDE.md`，二者现已字节级一致（Compare-Object 无差异）。

### 6. 赛道档案"待确认"补标注（任务六）
- **问题**：24 份档案六个必需章节（题面主题/任务拆解/方法谱系/推荐路线/避坑/来源）齐全，但有 7 处裸 `- 待确认。`（2023A/B、2024B/C/D、2025A/F），均位于"官方硬约束/提交格式"栏。
- **判定**：官方提交格式/硬约束**无法从获奖论文卡片推出**（获奖论文不记录当届官方模板），属"证据不足"而非"可补全"。
- **修复**：逐处改写为"**证据不足，待补充**：……须查当届官方通知核对"；2025 两份额外注明"无获奖论文简卡/深卡"。未编造任何方法/数字。
- **复核**：2023 A/B（Wave4-C 补强）结构完整——含逐 paper_id 方法拆解表、补强推荐路线、避坑、来源，判型提醒（2023A 本质 mechanism 而非 simulation）到位。

---

## 二、playbook 引用完整性（任务三，0 修复）

- 51 张方法卡（排除各原型 `00_overview.md`）**全部含"证据等级"行**：A=49、B=2、C=0，无未标注。
- 正则 `[年-赛道-paper_id]` 共提取 **125 条**引用（含 23 条带 `-p.x` 页码后缀，已正确剥离）。
- 逐条对 `corpus/papers_index.json`（729 个 paper_id）核验：**125 存在 / 0 缺失 / 0 需修复**。
- 结论：引用真实性本项干净，无需改动。

---

## 三、数字一致性核对（任务五，全部对得上）

| 文档声称 | 实算 | 结论 |
|---|---|---|
| 简卡 729 / 深卡 80 / 方法同义词 67 | `corpus_cards.py --stats` = 729/80/67 | ✅ |
| 方法卡 51 张 | 8 原型非 overview 文件计数 = 51 | ✅ |
| 奖级 1 一等奖+12 数模之星+716 待确认 | papers_index 实算 = 1/12/716 | ✅ |
| 深卡年份 2024=24、2021=18、2014/2022=5、2017/2018=3，其余 1–2 | 实算完全一致，合计 80 | ✅ |
| 验证覆盖 89.8%；与基线对比423/误差252/鲁棒187/交叉验证27/灵敏度18/蒙特卡洛7/ROC5/消融1 | `corpus/cards/AGGREGATE_STATS.md` 一致 | ✅ |
| 图表类型 折线163/流程158/结构153/示意141/对比雷达53/散点48/柱41/三维41 | AGGREGATE_STATS 图表 Top15 一致 | ✅ |
| figure-atlas PNG 19 张 | 实算 19 个 .png | ✅ |

---

## 四、模块与 SKILL.md 路由审查（任务一）

- **路径存在性**：SKILL.md 与 20 个模块引用的脚本/文档/卡片路径全部解析成功。表面"缺失"均为：
  - 脚本简写（`audit_tex.py` 等实居 `scripts/`，表格首行已给 `scripts/` 前缀）；
  - 语料聚合文件（`AGGREGATE_STATS.md`/`S3_star_patterns.md` 实居 `corpus/cards/`）；
  - 上游出处指针（`华为杯_求解规范/*.md`，模块内已注明"原文位置见 `docs/UPSTREAM.md`"，非仓库内待开文件）；
  - 运行期产物（`题目/reading_audit.md`、`evidence-ledger.json`、`page_targets.json`）。
- **TODO/TBD/占位**：模块/SKILL/playbook/tracks 内无真占位命中；`队号占位`、`无残留 TODO` 等均为字段名或门禁规则，非未完成项。
- **P0–P6 门禁四处一致**：SKILL.md §2、`docs/PHASE_GATES.md`、`docs/ACCEPTANCE.md`、`scripts/progress.py` 阶段名称 P0–P6、必做产物、**P1 硬退出（无用户确认记录=不通过）**逐条一致。
- **命令实跑**（≥10 条 `--help`/功能）：progress / playbook_match / evidence / review / submission_audit / visual_plan_init / build_latex / audit_tex / contest_init / build_docx 全部退出码 0；`corpus_cards.py --stats` 复现成功。

---

## 五、不修 / 待集成阶段闭环（记录）

### 5.1 其他分片正在改，本波只记录不动手
- **technical-roadmap 相关（Wave5-A）**：`modules/technical-roadmap.md` 引用 `scripts/audit_roadmap.py`、`scripts/render_roadmap.py`、`references/color-palettes.md`。我勘察时 `render_roadmap.py` 已落盘、`audit_roadmap.py` 与 `assets/roadmap/` 由 A 并行新增中。**待 A 完成后由 E 阶段复核引用闭环**。
- **doctor / quickstart / CI（Wave5-C）**：`scripts/doctor.py`、`tests/test_doctor.py`、`scripts/quickstart_demo.ps1`、`assets/scaffold/` 改动均为 C 的域，未触碰。
- **abstract / deai-writing / innovation / validation / FIGURE_COOKBOOK（Wave5-D）**：`modules/abstract.md`、`deai-writing.md`、`innovation.md`、`validation.md`、`figures-interface.md`、`paper-writing.md`、`kickoff-audit.md`、`submission.md`、`docs/FIGURE_COOKBOOK.md`、`docs/TROUBLESHOOTING.md` 均为 D 并行修改中，未触碰。
- **playbook 各原型 `00_overview.md`**：8 份正被某分片修改中，未触碰。

### 5.2 留待 Wave5-E 统一
- **脚本计数**：`交付说明.md` 写"`scripts/` 下 18 个 .py"。我勘察基线时因 A/C 并行新增 `doctor.py`、`render_roadmap.py` 已变为 20 个 .py。此数随集成继续变，**版本号与最终脚本计数统一留 E**。
- **版本号**：当前所有"当前版本"表述一致为 **v0.2.0**（无 v0.1/v0.3 混用漂移）；按约定升 **v0.3.0** 由 E 统一执行，本波不提前改。

### 5.3 设计使然 / 已在文档中诚实标注，不改
- `AGENTS.md`/`CLAUDE.md` 仍写"Wave0（当前）"：属历史阶段叙事，非版本号；镜像已字节一致，叙事更新留 E 一并处理。
- `corpus/cards/AGGREGATE_STATS.md` §八自陈"2014/2015 赛道主题疑似 Wave1 串号""2025 仅 C 级商业思路""奖级正文极少自述"——均为已诚实标注的已知局限，不属违例。

### 5.4 仓库卫生提示（非阻断）
- 仓库根存在 `_work/patch_test.py`（gitignore 内）引用旧版"豁免清单"测试文本；从仓库根直接 `pytest` 会因收集它而中断。**正确跑法是 `pytest tests/`**（文档已如此写）。建议集成后清理 `_work/` 临时脚本。

---

## 六、自审结论

- [x] 两张指定深卡手动 schema 校验 VALID，全 80 张 0 违例，测试无豁免清单。
- [x] playbook 125 条引用全部存在于索引，0 缺失。
- [x] 文档统计数字（729/80/67/51/1+12+716/深卡年份/图表与验证计数）均可由脚本重算，已逐项对上。
- [x] 赛道档案补充的"证据不足"标注均有依据（官方模板不在语料），未编造任何方法/数字；2023 A/B Wave4-C 补强复核通过。
- [x] 未触碰其他分片文件；未升版本号；Desktop 语料只读。
