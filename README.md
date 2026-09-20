# Huaweibei-cool · 华为杯研赛国一母 Skill

以 2004–2024 共 **729 篇**华为杯（中国研究生数学建模竞赛）获奖论文为底座的母 Skill，
把“建模—求解—论文—打磨—赛后蒸馏”全流程固化为模块、playbook 与赛道档案。

> 当前为 **Wave0**：语料勘察、仓库骨架、卡片 schema、v2.1 工程资产移植。模块正文与
> 赛道档案在 Wave1–Wave3 充实。

## 安装

```powershell
git clone <repo>
cd Huaweibei-cool
python -m pip install -r requirements.txt
```

依赖：pymupdf、pypdf、python-docx、pytest（Wave0 已实测可导入）。

## 目录结构

```
SKILL.md            母 Skill 入口与路由
config/             比赛配置与 JSON Schema
modules/            流程模块（求解/图/验证/比赛日/训练/打磨/蒸馏）
playbooks/          方法卡（Wave1）
tracks/             赛道档案（Wave1）
corpus/
  papers_index.json/.csv   729 篇语料索引（已入库）
  text/                    全文抽文（.gitignore 排除，本地生成）
  schemas/                 四类卡片 JSON Schema
  cards/                   产出的简卡/深卡（入库）
scripts/            语料与论文链脚本
skills/academic-figure/  科研绘图子 skill（移植自 v2.1，去重保留一份）
assets/paper-template/   论文 LaTeX/Word 模板
assets/scaffold/         比赛日空骨架
docs/UPSTREAM.md          上游资产来源与许可记录
tests/              测试
```

## 比赛日 1-2-3 上手

1. 运行 `START_WINDOWS.bat`（或 `python scripts/contest_init.py`）初始化工作目录。
2. 按 `config/contest.json` 核对当届官方规则（届次、页数、格式）。
3. **反 AI 读题审计**：按 `modules/kickoff-audit.md` 逐段拆解题面、列约束与歧义、出建模候选与图表计划；
   **报告先给用户确认，确认记录写入 evidence-ledger，才允许进入求解**（判型器只出候选，不抢跑）。
4. 从 `SKILL.md` 的启动选择题路由进入对应模块。

> **反 AI 命题意识**：出题组会刻意诱导套路、藏约束、设歧义。宁可慢、宁可多问，
> 也不许凭模式匹配一眼套模板就开干——千万不要聪明反被聪明误。

## 红线

- Desktop 语料根只读，不修改/移动/删除任何用户文件。
- PDF、全文抽文 txt、渲染 PNG 不入 git（见 `.gitignore`）。
- 数字、奖级、方法归属拿不准标“待确认”，禁止脑补。
