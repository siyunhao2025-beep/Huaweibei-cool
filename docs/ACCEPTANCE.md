# docs/ACCEPTANCE.md · 验收标准

> 本仓库 Wave0–Wave2 完成后的交付物清单与验收条件。

## 1. 知识库

- [ ] `playbooks/`：8 原型 51 方法卡 + INDEX.md + match_rules.json 存在。
- [ ] `tracks/`：2022–2025 共 24 题档案 + README + track-selection-stats 存在。
- [ ] `corpus/cards/`：729 简卡（brief/）+ 80 深卡（deep/）+ AGGREGATE_STATS/S3/S4 存在。
- [ ] `corpus/problem_analysis/`：innovation_algorithms/ai_prompts_distilled/CODE_INVENTORY 存在。

## 2. 模块（modules/ 20 个）

- [ ] workflow/phases/kickoff-audit/track-selection/problem-typing/solving/validation/evidence-ledger/figures-interface/paper-writing/abstract/deai-writing/innovation/submission/review-panel/polishing/change-management/distillation/matlab-conventions/training 全部存在且非空。

## 3. 反 AI 读题审计（硬要求）

- [ ] `modules/kickoff-audit.md` 含：反 AI 陷阱清单（≥7 类）+ 逐段拆解四元组流程 + 读题审计报告 7 节 + 人工确认门禁。
- [ ] `modules/problem-typing.md` 明确：判型器只出候选原型假设，须经题面证据质证与用户确认，禁止"判型=定模型"。
- [ ] `modules/figures-interface.md` 明确：图表计划源自读题审计报告 §6 且经用户确认后才执行。
- [ ] P1 门禁定义为硬退出：**无用户确认记录 = 不通过**（见 `docs/PHASE_GATES.md`）。
- [ ] SKILL.md 硬规则含"反 AI 读题：未确认不得求解"；启动路由 C 提示先过读题审计。
- [ ] tests 含正反例：**无用户确认记录不得进入求解**（Wave3 负责实现）。

## 4. 脚本可运行

- [ ] `scripts/playbook_match.py --help` 退出 0。
- [ ] `scripts/evidence.py --help` 退出 0。
- [ ] `scripts/progress.py --help` 退出 0。
- [ ] `scripts/review.py --help` 退出 0。
- [ ] `scripts/submission_audit.py --help` 退出 0。
- [ ] 功能验证：playbook_match 出推荐方法卡；progress 空目录 FAIL；evidence 能报问题；review 出四维分；submission_audit 能查 PDF/tex。

## 5. 文档

- [ ] `docs/SCORING_RUBRIC.md` 四维度量表+自评清单+官方来源标注。
- [ ] `docs/DISTILLATION_METHOD.md` 含留出盲检 10 篇（含失败案例）。
- [ ] `docs/PHASE_GATES.md` / `ACCEPTANCE.md` / `ARCHITECTURE.md` / `PEER_COMPARISON.md` / `CHANGELOG.md` 齐全。

## 6. SKILL.md

- [ ] 移除"Wave0 骨架版"标记。
- [ ] 模块路由表含全部 20 模块（状态"已完成"）。
- [ ] ≤500 行，frontmatter 仅 name/description。

## 7. 引用真实性

- [ ] 模块中引用的 playbook/方法卡/赛道档案路径真实存在（见 ARCHITECTURE）。

## 8. 优秀论文自检表（Wave6）

- [ ] `assets/checklists/paper_checklist.json` **138 条齐全**（F01–F06 / L01–L17 / A01–A10 / B01–B15 / T01–T08 / H01–H06 / S01–S06 / C01–C08 / P01–P11 / M01–M14 / Q01–Q09 / V01–V07 / W01–W05 / E01–E08 / I01–I02 / G01–G02 / R01–R02 / X01–X02）；人读版与 JSON 文案逐 ID 一致，V05 为数据结构感知划分，主观条目不得伪装成机检硬失败。
- [ ] 机检脚本 `scripts/paper_checklist.py` 对**正/反例 fixture 行为正确**（正例 PASS、反例 FAIL）。
- [ ] P6 门禁检查已勾选自检表存在（`progress.py --gate P6` 查《论文自检表_已勾选.md》与 sidecar 无未裁决项）。
- [ ] 未做到条目**显式标注"不适用/未做到+原因"+ 用户确认**，不静默跳过。
- [ ] P4 门禁检查比赛工作目录下存在自检表文件（`论文/优秀论文自检表.md`）。

## 验收结论

Wave2B 完成后，以上全部勾上即验收通过。
