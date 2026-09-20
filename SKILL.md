---
name: huawei-mcm
description: 华为杯（中国研究生数学建模竞赛）AI 作战中枢。覆盖赛前训练、比赛日全流程、单题卡点求助、论文打磨、赛后蒸馏五类场景。当用户要准备或参加华为杯研赛、需要按获奖论文范式建模/求解/写论文、或要对一道赛题做方法选型与论文成稿时触发。不用于普通课程作业、非数学建模的科研论文、或纯绘图需求（绘图走 academic-figure 子 skill）。
---

# Huaweibei-cool · 华为杯研赛 AI 作战中枢

以 2004–2024 共 729 篇获奖论文语料为底座，把"建模—求解—论文—打磨—赛后蒸馏"
固化成 20 个任务契约模块、8 原型 51 张方法卡、24 题赛道档案与一组门禁脚本。
知识库蒸馏方法与已知局限见 `docs/DISTILLATION_METHOD.md`。

## 0. 启动选择题路由

用户进入后，先按意图选一条主路（不要一次全跑）：

| 选项 | 场景 | 进入模块 |
|---|---|---|
| A | 赛前训练：刷题、方法体系、模拟赛 | `modules/training.md` |
| B | 比赛日全流程：题面到提交 | `modules/workflow.md` + `modules/phases.md`，先跑 `scripts/contest_init.py` |
| C | 单题卡点：某问建模/求解卡住 | **先过读题审计**（`modules/kickoff-audit.md`），再 `modules/solving.md` + `modules/validation.md` |
| D | 论文打磨：成稿/排版/审校 | `modules/polishing.md` + `modules/figures-interface.md` |
| E | 赛后蒸馏：复盘、方法卡沉淀 | `modules/distillation.md` |

## 1. 模块路由表（全部已完成）

| 模块 | 职责 |
|---|---|
| `modules/workflow.md` | 比赛日 72h 全流程时间线与阶段交接 |
| `modules/phases.md` | P0–P6 阶段契约详表（内容级门禁） |
| `modules/kickoff-audit.md` | 反 AI 读题审计：陷阱清单/逐段拆解/审计报告/用户确认门禁 + 规则/数据/环境 |
| `modules/track-selection.md` | 选题决策（字母按届重置） |
| `modules/problem-typing.md` | 题面→8 原型匹配流程 |
| `modules/solving.md` | 求解主线：读题→假设→建模→算法→结果 |
| `modules/validation.md` | 验证门禁：误差/对比/灵敏度/消融 |
| `modules/evidence-ledger.md` | 证据账本与 AI 来源标注 |
| `modules/figures-interface.md` | 论文图规范与求解图接口 |
| `modules/technical-roadmap.md` | 技术路线图（论文图1）：YAML 规格 + 8 原型模板 + 渲染/审计脚本 |
| `modules/paper-writing.md` | 论文章节结构与页数基线 |
| `modules/abstract.md` | 摘要写法专项（国一模板） |
| `modules/deai-writing.md` | 反模板/反 AI 味写作 |
| `modules/innovation.md` | 创新点提炼与伪创新识别 |
| `modules/submission.md` | 提交规范与 AI 披露 |
| `modules/review-panel.md` | 评审团模拟自评 |
| `modules/polishing.md` | 打磨审校与数字一致性 |
| `modules/change-management.md` | 比赛中变更管理与回退 |
| `modules/distillation.md` | 赛后蒸馏与方法卡沉淀 |
| `modules/matlab-conventions.md` | MATLAB 工程规范 |
| `modules/training.md` | 赛前训练计划 |

## 2. 阶段契约 P0–P6 一览

| 阶段 | 名称 | 必做产物 | 门禁 |
|---|---|---|---|
| P0 | 环境初始化 | 目录骨架、contest.json | 题面/规则落盘 |
| P1 | 读题与拆解 | 逐段拆解、读题审计报告、题型候选 | **读题审计报告已产出且经用户明确确认（确认记录写入 evidence-ledger）** |
| P2 | 建模 | 假设≥3、模型链、基线 | 基线跑通 |
| P3 | 求解 | 代码、结果、验证 | 可复现+≥1验证 |
| P4 | 论文初稿 | 摘要/正文/结论 | 章节齐、摘要≤2页 |
| P5 | 打磨审校 | 终稿、匿名化、引用 | audit 脚本 PASS |
| P6 | 提交蒸馏 | 提交包、AI披露、复盘 | 提交审计 PASS |

详细工程化检查命令见 `docs/PHASE_GATES.md`。

## 3. 硬规则（不可覆盖）

1. **题面优先**：一切以当届官方题面与官方规则为准；本仓库经验值只在官方未规定时兜底。
2. **反 AI 读题（硬门禁）**：出题组会"反 AI"命题（诱导套路/隐藏约束/歧义陷阱）。
   禁止凭模式匹配或判型器直接定模型；必须先出读题审计报告（逐段拆解+约束+歧义+建模候选+图表计划），
   **未经用户确认不得进入求解**；用户确认记录写入 evidence-ledger。宁可慢、宁可多问，不抢跑。
   详见 `modules/kickoff-audit.md`。
3. **禁伪造**：数字、方法归属、实验结果不得编造；拿不准标"待确认"并给置信度。
4. **证据留痕**：每个关键结论可回溯到代码/数据/页码；语料引用标注 `年-赛道-paper_id-页码`。
5. **AI 披露（2026 规定）**：AI 仅作辅助，不替代独立思考与核心创新；AI 输出须理解后用、用自己的话写；
   辅助写作/数据分析/编程均按规定标注（工具名/版本/机构/日期）；无来源模型公式一律不写；违反取消评奖资格。
   细则见 `modules/submission.md`、`docs/SCORING_RUBRIC.md`。
6. **官方规则最高**：页数/格式/署名/提交方式以官方通知覆盖本仓库任何默认。
7. **不承诺获奖**：本 skill 提升工程与表达质量，不承诺任何奖项结果。
8. **语料只读**：Desktop 获奖论文语料根只读，不删除/移动/重命名任何用户文件。
9. **赛道字母按届重置**：A–F 只是当年题号，不跨届固定含义。

## 4. 本地脚本索引

| 脚本 | 用途 |
|---|---|
| `scripts/contest_init.py` | 比赛日初始化工作目录骨架 |
| `scripts/corpus_build.py` / `corpus_cards.py` | 语料抽文与卡片（已跑通 729 篇） |
| `scripts/build_latex.py` / `audit_tex.py` / `audit_paper.py` | LaTeX 论文构建与审计 |
| `scripts/build_docx.py` / `audit_docx.py` | Word 论文构建与审计 |
| `scripts/visual_plan_init.py` / `visual_plan_audit.py` | 论文视觉计划 |
| `scripts/playbook_match.py` | 题面→原型/方法卡规则匹配 |
| `scripts/evidence.py` | 证据账本合规校验 |
| `scripts/progress.py` | P0–P6 内容级门禁（`--gate Pn` / `--all`） |
| `scripts/review.py` | 评审团启发式打分（非真评审） |
| `scripts/submission_audit.py` | 提交前审计（页数/匿名/AI披露/附件） |
| `scripts/doctor.py` | 一键环境自检（Python/依赖/TeX/字体/MATLAB/Word） |
| `scripts/render_roadmap.py` | 技术路线图渲染（YAML→PNG/PDF/MMD/DOT） |
| `scripts/audit_roadmap.py` | 技术路线图规格审计（schema+图结构+安全色） |

## 5. 评分与自评

- 官方四标准：假设合理性、建模创造性、结果正确性、文字表述清晰度。
- 自评量表与锚点见 `docs/SCORING_RUBRIC.md`（经验推断，非官方细则）。
- 知识库蒸馏方法与留出盲检结果见 `docs/DISTILLATION_METHOD.md`。
- 论文图种选型与八原型必备图清单见 `docs/FIGURE_COOKBOOK.md`。
- 环境/编译/字体常见坑与修复见 `docs/TROUBLESHOOTING.md`。
- 一键开箱玩具样例见 `docs/examples/quickstart/`（题面→匹配→路线图→xelatex 全链路）。

## 6. 完成报告纪律

每轮任务结束，按三态回报：**implemented**（已实现）、**tested**（已跑通验证）、
**live-validated pending**（待比赛日/真机验证）。不把"写完脚本"说成"跑通脚本"。
