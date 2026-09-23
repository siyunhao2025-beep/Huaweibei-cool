# docs/PHASE_GATES.md · P0–P6 阶段门禁（工程化）

> 与 `modules/phases.md` 对应，本表给出每个门禁的**检查命令/脚本**。门禁是内容级，不是文件存在级。

| 阶段 | 门禁 | 检查方式 |
|---|---|---|
| P0 | 题面/规则落盘；contest.json 填好；环境可跑 | `python scripts/progress.py --root <工作目录> --gate P0`；`python scripts/contest_init.py` 自检 |
| P1 | **读题审计与 Figure 建议总数均经用户明确确认**；逐段拆解；题型候选 | `--gate P1`（查报告、确认记录与视觉计划 1.2 图数锁）；`python scripts/playbook_match.py --txt 题面.txt`（仅出候选） |
| P2 | 假设 ≥3 条；目标函数；baseline 脚本 | `--gate P2` |
| P3 | 求解代码；结果落盘；≥1 验证；Figure 数量锁有效；有候选改进时用户已完成策略选择 | `--gate P3`；`visual_plan_audit.py --stage plan/render`；证据与用户裁决入 `scripts/evidence.py --ledger` |
| P4 | 用户已裁决完整 PDF 长度；摘要/结论/章节齐；**分章节对照自检表逐条勾选** | `--gate P4`（篇幅裁决 + 章节齐全 + 检查比赛工作目录下存在 `论文/优秀论文自检表.md`） |
| P5 | 无 TODO；引用；封皮后匿名化；LaTeX Figure 数等于用户锁定值；复杂 F01 审计绑定当前产物 | `--gate P5`；`visual_plan_audit.py --stage paper`；`python scripts/audit_tex.py`/`audit_docx.py`；复杂 F01 另生成 `F01_framework_audit.json`；`python scripts/review.py --paper 论文.txt` |
| P6 | 全量求解链与交付包同源；附件齐；AI 披露；最终 PDF；**自检表与提交审计均绑定当前产物并现场复核** | 先完成人工可核验的全量重跑/干净构建/交付清单，再生成 `论文/submission_audit.json`，运行 `python scripts/progress.py --root . --gate P6`；门禁会现场重算 paper checklist 机器项并重跑 submission audit |

## 一键全检

```
python scripts/progress.py --root <工作目录> --all
```

退出码 0=全过，1=有未过项。空目录应全 FAIL，完整目录才 PASS。

## 门禁内容级标准（摘要）

- **P1（硬退出，不可绕过）**：读题审计报告（逐段拆解四元组 + 约束 Cx + 歧义 Qx + 建模候选 + 逐图清单/建议总数）已产出，
  且**读题裁决与 Figure 总数均有用户明确确认记录**（分别写进 evidence-ledger 与 `求解/视觉计划.json`）。任一确认缺失 = P1 不通过，禁止进入 P2 求解。
  `progress.py --gate P1` 做启发式检查（查报告文件与确认关键词）；但即使脚本因实现成本查不出，
  本规则也是**不可违反的流程规则**：脚本漏检不构成跳过理由。判型器只出候选，未经质证+确认不采信。
- P2：模型假设检出 ≥3 条编号行（`count_assumptions`）。
- P3：存在 `.m/.py` + `.mat/.csv/.json` + 含"误差/对比/灵敏度/消融"等验证关键词或文件；视觉计划 1.2 的锁定值与 Figure/Schematic 数一致；若提出候选改进，还须有同口径比较证据与用户策略裁决。该条件分支由人工核对，脚本未识别候选不构成绕过理由。
- **P4（篇幅裁决 + 分章节清单）**：Figure 锁定后，用户已选择具体总页数或“证据充分即可”；章节齐全（摘要/结论/主要章节）；题目、完整摘要和关键词共同占一个逻辑页且正文从下一页开始；并且**每完成一个章节即对照自检表勾选**——比赛工作目录下应存在 `论文/优秀论文自检表.md`。写作阶段边写边勾，不堆到最后。单页摘要是用户内部规则，官方原文仍为“一般不超过两页”。
- P5：全文无 TODO/占位；除第 0 页官方封皮外无学校、姓名或队号字样；`visual_plan_audit.py --stage paper` 确认最终 LaTeX 顶层 Figure 数与用户锁定值一致；反 AI 味人工清单闭环。若视觉计划声明复杂多问 F01，或项目中已有 `F01_framework_binding.json`，还必须用 `audit_framework_figure.py --stage paper` 生成同目录 `F01_framework_audit.json`；P5 会现场重跑并拒绝缺失、非 PASS、错绑或陈旧报告。普通无 F01 稿件不触发该门禁。
- **P6（自检表 100% 闭环，硬性退出）**：
  1. 原始题面/数据校验值、权威源码入口、运行顺序、缓存清单和旧件备份均有记录；派生缓存已失效，求解—验证—图表—论文链已全量重跑，关键结果与冻结版的差异均已解释；
  2. 权威目录双遍编译和隔离目录干净构建已完成，页数、页面尺寸、规范化文本及固定 DPI 渲染指纹一致；最终 PDF 已逐页目检；全部交付别名、源码/Overleaf 包、复现包、说明和 SHA-256 清单来自同一冻结快照，源码包解压后可重编；
  3. **`paper_checklist.py` 机检 0 ❌**（`--strict` 退出码 0）；
  4. **人工条目全部裁决**：sidecar（`paper_checklist_decisions.json`）中无未裁决人工条目（☐）；每条做到 ✅ 或显式标注"不适用/未做到+原因"并经用户确认；
  5. 已勾选报告、sidecar 与当前 TeX 主稿位于同一工作链，provenance 绑定当前清单、参数与文件哈希；P6 会现场重算全部机器项并逐项比较，不能用手工全绿报告代替；
  6. `论文/submission_audit.json` 由正式最终 PDF、paper checklist 所绑定的同一 TeX 主稿、与该主稿输入链唯一匹配的原始 manifest、非空 `提交附件/`、明确 AI 使用方式及 AI 说明文件生成；命令显式传入 `--manifest 论文输入.json`，或由主稿同目录唯一自动发现。provenance 同时绑定 manifest 相对路径和 SHA-256；P6 会带同一 manifest 现场重跑，删除、替换或错绑 manifest 均不放行；
  7. 复杂 F01 的 binding 必须把 `main_tex` 指向上述同一 TeX 主稿、把 `compiled_pdf` 指向上述最终提交 PDF；paper-stage 报告须与 binding 同目录，P6 现场重跑后逐项一致。无复杂 F01 时明确不适用，不要求空造报告；
  8. `submission_audit.py` 复用 `audit_paper.py` 的成品页审计：物理第 2 页须完整容纳题目、摘要和关键词，正文从物理第 3 页开始，题目行数/平衡与摘要字号合规；manifest 必须且只能声明一个 `references` 角色，检测到附录标题时必须有对应 `appendix` 角色，参考文献及每个已声明附录都须从物理页首开始。纯无附录稿合法，但不能缺参考文献角色；两项结果均写入结构化 `checks` 并受 provenance 哈希保护；
  9. **《论文自检表_已勾选.md》落盘**：比赛工作目录下存在该已勾选表；
  10. **无用户确认记录 = 门禁不通过**（与 P1 一致，保持不削弱）。
  任一不满足 = P6 不通过，禁止提交。
- P6 的目录/关键词/PDF 结构检查只作快速预检；paper checklist 与 submission audit 可现场复核其覆盖的来源和版式，但不能自动证明任意项目的全部数值缓存都已失效、每个外部脚本都已执行或每份压缩包都已人工抽查。前两项须保留运行日志、差异对账、逐页 QA 与校验清单作为人工证据，脚本 PASS 不能替代。

## 注意

- 这些是启发式内容检查，不能替代人工评审；漏报/误报都可能。
- 当届官方格式要求覆盖本仓库任何默认。
