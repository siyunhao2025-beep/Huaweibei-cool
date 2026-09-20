# AGENTS.md · 工作纪律与阶段门禁

本文件与 CLAUDE.md 同源镜像。所有在本仓库工作的 agent 必须遵守。

## 阶段门禁（Wave0→Wave3）

- **Wave0（当前）**：语料勘察、仓库骨架、卡片 schema、v2.1 资产移植。产出：729 篇索引、schema、可跑脚本。
- **Wave1**：全量简卡 + ≥80 篇深卡，卡片必须过 `corpus/schemas/` 校验。
- **Wave2**：填充 modules/、playbooks/、tracks/ 正文，方法频次统计。
- **Wave3**：比赛日全流程真机验证、example.tex 编译、统一 git commit。

## 工作纪律

1. **语料只读**：Desktop 获奖论文语料根只读，禁止删除/移动/重命名。
2. **反 AI 读题（不可跳过的硬环节）**：出题组会“反 AI”命题（诱导套路/隐藏约束/歧义陷阱）。
   读题审计（`modules/kickoff-audit.md`）不可跳过；**禁止抢跑下结论**——判型器只出候选原型，
   不得据此直接定模型。读题审计报告必须经用户明确确认，确认记录写入 evidence-ledger 后才允许求解；
   无确认记录 = P1 门禁不通过。宁可慢、宁可多问，不聪明反被聪明误。
3. **证据留痕**：引用获奖论文一律标注 `年-赛道-paper_id-页码`。
4. **拿不准就标待确认**：奖级、方法、数字置信度不足时显式标注，不脑补。
5. **三态回报**：implemented / tested / live-validated pending，不混淆“写了”与“跑通了”。
6. **脚本先 --help**：移植脚本改完路径后必须 `python scripts/<name>.py --help` 验证 import 不报错。
7. **不入大文件**：PDF、txt、PNG 渲染产物一律 .gitignore 排除。

## 常用命令

```powershell
# 全量语料抽文（断点续跑）
python scripts/corpus_build.py
# 强制重扫
python scripts/corpus_build.py --rescan
# 比赛日初始化
python scripts/contest_init.py --help
```
