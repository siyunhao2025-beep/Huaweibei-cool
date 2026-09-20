# docs/PHASE_GATES.md · P0–P6 阶段门禁（工程化）

> 与 `modules/phases.md` 对应，本表给出每个门禁的**检查命令/脚本**。门禁是内容级，不是文件存在级。

| 阶段 | 门禁 | 检查方式 |
|---|---|---|
| P0 | 题面/规则落盘；contest.json 填好；环境可跑 | `python scripts/progress.py --root <工作目录> --gate P0`；`python scripts/contest_init.py` 自检 |
| P1 | **读题审计报告已产出且经用户明确确认**；逐段拆解；题型候选 | `--gate P1`（启发式查报告与确认记录）；`python scripts/playbook_match.py --txt 题面.txt`（仅出候选） |
| P2 | 假设 ≥3 条；目标函数；baseline 脚本 | `--gate P2` |
| P3 | 求解代码；结果落盘；≥1 验证 | `--gate P3`；证据入 `scripts/evidence.py --ledger` |
| P4 | 摘要/结论/章节齐 | `--gate P4` |
| P5 | 无 TODO；引用；匿名化 | `--gate P5`；`python scripts/audit_tex.py`/`audit_docx.py`；`python scripts/review.py --paper 论文.txt` |
| P6 | 附件齐；AI 披露；最终 PDF | `--gate P6`；`python scripts/submission_audit.py --paper 论文.pdf --ai-file AI披露.txt --attachments 提交附件` |

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
- P3：存在 `.m/.py` + `.mat/.csv/.json` + 含"误差/对比/灵敏度/消融"等验证关键词或文件。
- P5：全文无 TODO/占位/学校姓名字样。
- P6：提交附件目录非空、文本含"AI/人工智能"披露、有 PDF。

## 注意

- 这些是启发式内容检查，不能替代人工评审；漏报/误报都可能。
- 当届官方格式要求覆盖本仓库任何默认。
