# Huaweibei-cool · 华为杯研赛 AI 作战中枢

![huawei-mcm](docs/banner.png)

**华为杯研赛 · AI 作战中枢**
729 篇获奖论文蒸馏 · 八大题型原型 · 从读题到提交全程护航

> 读懂题 · 建对模 · 写好论文 · 稳交卷
>
> 别人在套模板，你在逐句读题、证据建模、步步为营。

以 2004–2024 共 **729 篇**华为杯（中国研究生数学建模竞赛）获奖论文为底座，
把"建模—求解—论文—打磨—赛后蒸馏"全流程固化为模块、playbook、赛道档案与质量门禁。

> GitHub About：华为杯中国研究生数学建模竞赛 AI 作战中枢：729 篇获奖论文蒸馏 ·
> 8 大题型原型 51 张方法卡 · 2022–2025 共 24 题赛道档案 · 反套路读题人工确认门禁 ·
> LaTeX/Word 双论文链路 · 全流程质量测试。

> **免责语**：本工具不承诺获奖、不代提交；AI 仅作辅助，须按当届官方规定披露使用情况。

## 安装

```powershell
git clone <repo>
cd Huaweibei-cool
python -m pip install -r requirements.txt
```

依赖：pymupdf、pypdf、python-docx、pytest（已实测可导入）。

## 目录结构

```
SKILL.md            Skill 入口与路由
config/             比赛配置与 JSON Schema
modules/            流程模块（求解/图/验证/比赛日/训练/打磨/蒸馏）
playbooks/          八大题型原型与方法卡
tracks/             2022–2025 赛道档案
corpus/
  papers_index.json/.csv   729 篇语料索引（已入库）
  text/                    全文抽文（.gitignore 排除，本地生成）
  schemas/                 卡片 JSON Schema
  cards/                   产出的简卡/深卡（入库）
scripts/            语料与论文链脚本
skills/academic-figure/  科研绘图子 skill
assets/paper-template/   论文 LaTeX/Word 模板
assets/scaffold/         比赛日空骨架
docs/UPSTREAM.md          上游资产来源与许可记录
docs/HANDOFF.md           深化交接包
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
- 数字、奖级、方法归属拿不准标"待确认"，禁止脑补。
- 本工具不承诺获奖、不代提交；AI 仅作辅助，须按当届官方规定披露使用情况。
