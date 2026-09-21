# docs/PHASE_GATES.md · P0–P6 阶段门禁（工程化）

> 与 `modules/phases.md` 对应，本表给出每个门禁的**检查命令/脚本**。门禁是内容级，不是文件存在级。

| 阶段 | 门禁 | 检查方式 |
|---|---|---|
| P0 | 题面/规则落盘；contest.json 填好；环境可跑 | `python scripts/progress.py --root <工作目录> --gate P0`；`python scripts/contest_init.py` 自检 |
| P1 | **读题审计报告已产出且经用户明确确认**；逐段拆解；题型候选 | `--gate P1`（启发式查报告与确认记录）；`python scripts/playbook_match.py --txt 题面.txt`（仅出候选） |
| P2 | 假设 ≥3 条；目标函数；baseline 脚本 | `--gate P2` |
| P3 | 求解代码；结果落盘；≥1 验证；有候选改进时用户已完成策略选择 | `--gate P3`；证据与用户裁决入 `scripts/evidence.py --ledger` |
| P4 | 摘要/结论/章节齐；**分章节对照自检表逐条勾选** | `--gate P4`（章节齐全 + 检查比赛工作目录下存在 `论文/优秀论文自检表.md`） |
| P5 | 无 TODO；引用；封皮后匿名化 | `--gate P5`；`python scripts/audit_tex.py`/`audit_docx.py`；`python scripts/review.py --paper 论文.txt` |
| P6 | 附件齐；AI 披露；最终 PDF；**自检表 100% 闭环（机检 0 ❌ + 人工条目全裁决 + 已勾选表落盘）** | `--gate P6`（含自检表门禁）；`python scripts/submission_audit.py --paper 论文.pdf --ai-file AI披露.txt --attachments 提交附件`；`python scripts/paper_checklist.py --strict` |

## 一键全检

```
python scripts/progress.py --root <工作目录> --all
```

退出码 0=全过，1=有未过项。空目录应全 FAIL，完整目录才 PASS。

## 门禁内容级标准（摘要）

- **P1（硬退出，不可绕过）**：读题审计报告（逐段拆解四元组 + 约束 Cx + 歧义 Qx + 建模候选 + 图表计划）已产出，
  且**存在用户明确确认记录**（写进 evidence-ledger）。**无用户确认记录 = P1 不通过，禁止进入 P2 求解。**
  `progress.py --gate P1` 做启发式检查（查报告文件与确认关键词）；但即使脚本因实现成本查不出，
  本规则也是**不可违反的流程规则**：脚本漏检不构成跳过理由。判型器只出候选，未经质证+确认不采信。
- P2：模型假设检出 ≥3 条编号行（`count_assumptions`）。
- P3：存在 `.m/.py` + `.mat/.csv/.json` + 含"误差/对比/灵敏度/消融"等验证关键词或文件；若提出候选改进，还须有同口径比较证据与用户策略裁决。该条件分支由人工核对，脚本未识别候选不构成绕过理由。
- **P4（分章节清单检查）**：章节齐全（摘要/结论/主要章节）；且**每完成一个章节即对照自检表勾选**——比赛工作目录下应存在 `论文/优秀论文自检表.md`（机检版 `assets/checklists/paper_checklist.json`，`progress.py --gate P4` 启发式查该文件存在）。写作阶段边写边勾，不堆到最后。
- P5：全文无 TODO/占位；除第 0 页官方封皮外无学校、姓名或队号字样。
- **P6（自检表 100% 闭环，硬性退出）**：
  1. **`paper_checklist.py` 机检 0 ❌**（`--strict` 退出码 0）；
  2. **人工条目全部裁决**：sidecar（`paper_checklist_decisions.json`）中无未裁决人工条目（☐）；每条做到 ✅ 或显式标注"不适用/未做到+原因"并经用户确认；
  3. **《论文自检表_已勾选.md》落盘**：比赛工作目录下存在该已勾选表；
  4. **无用户确认记录 = 门禁不通过**（与 P1 一致，保持不削弱）。
  任一不满足 = P6 不通过，禁止提交。
- P6：提交附件目录非空、文本含"AI/人工智能"披露、有 PDF。

## 注意

- 这些是启发式内容检查，不能替代人工评审；漏报/误报都可能。
- 当届官方格式要求覆盖本仓库任何默认。
