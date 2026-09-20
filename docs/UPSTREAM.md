# docs/UPSTREAM.md · 上游资产来源与许可记录

本文件记录 Huaweibei-cool 仓库中所有移植/提炼自上游的资产、其原始位置与许可。
Wave0 整理，后续新增上游资产时追加。

## 一、v2.1 工程包（上游主来源）

- 上游根：`zip_extract/huawei_skillsv2_v2.1_competition_ready`（只读参考）
- 版本：v2.1（见其 `VERSION.txt` / `V2.1_更新说明.md`）

### 1. 论文模板资产 → `assets/paper-template/`

| 上游文件 | 目标 | 说明 |
|---|---|---|
| `华为杯_论文规范模板/gmcmthesis.cls` | `assets/paper-template/gmcmthesis.cls` | 论文文档类 |
| `华为杯_论文规范模板/gmcm.bst` | 同名 | 参考文献样式 |
| `华为杯_论文规范模板/gmcm-title.sty` | 同名 | 标题样式 |
| `华为杯_论文规范模板/example.tex` | 同名 | 示例论文 |
| `华为杯_论文规范模板/reference.bib` | 同名 | 示例文献库 |
| `华为杯_论文规范模板/page_targets.json` | 同名 | 页数目标 |
| `华为杯_论文规范模板/agent_manifest.schema.json` | 同名 | 论文清单 schema |
| `华为杯_论文规范模板/章节页数基线.json` | 同名 | 章节页数基线 |
| `华为杯_论文规范模板/章节模板/` | `assets/paper-template/章节模板/` | 各章节 .tex 模板 |
| `华为杯_论文规范模板/figures/` | `assets/paper-template/figures/` | 论文图占位/logo |
| `华为杯_论文规范模板/华为杯_论文章节规范.md` | 同名 | 章节规范 |
| `研赛论文Word标准模板.docx` | `assets/paper-template/研赛论文Word标准模板.docx` | Word 官方模板 |

> 许可：gmcmthesis 类模板及其随附文件保留其原始许可声明（见模板目录内 README）。
> 本仓库不改动其版权归属。

### 2. 论文链脚本 → `scripts/`

| 上游 | 目标 |
|---|---|
| `华为杯_论文规范模板/tools/build_latex.py` | `scripts/build_latex.py` |
| `.../tools/audit_tex.py` | `scripts/audit_tex.py` |
| `.../tools/audit_paper.py` | `scripts/audit_paper.py` |
| `.../tools/build_docx.py` | `scripts/build_docx.py` |
| `.../tools/audit_docx.py` | `scripts/audit_docx.py` |
| `.../tools/migrate_markdown_to_tex.py` | `scripts/migrate_markdown_to_tex.py` |
| `.../tools/calibrate_page_targets.py` | `scripts/calibrate_page_targets.py` |
| `.../tools/render_word.vbs` | `scripts/render_word.vbs` |

修改：每个 .py 头部加 `# [来源]` 注释；路径均为 CLI 参数驱动，无需改绝对路径。
Wave0 已逐个 `--help` 验证 import 不报错（编译链路 Wave3 验证）。

### 3. 视觉计划脚本 → `scripts/`

| 上游 | 目标 |
|---|---|
| `华为杯_求解规范/tools/init_visual_plan.py` | `scripts/visual_plan_init.py` |
| `华为杯_求解规范/tools/audit_visual_plan.py` | `scripts/visual_plan_audit.py` |
| `华为杯_求解规范/视觉计划.schema.json` | `scripts/视觉计划.schema.json` |

### 4. 求解/绘图规范 → 提炼进 `modules/`（非原样复制）

| 上游原文 | 提炼去向 |
|---|---|
| `华为杯_求解规范/华为杯_求解规范.md`（63KB） | `modules/solving.md` 骨架（Wave2 充实） |
| `华为杯_求解规范/华为杯_绘图规范.md`（31KB） | `modules/figures-interface.md` 骨架（Wave2 充实） |

### 5. 比赛配置与初始化 → 演进

| 上游 | 目标 |
|---|---|
| `比赛配置.json` + `比赛配置.schema.json` | `config/contest.json` + `config/contest.schema.json`（演进：加附录门禁、corpus 块、届次待确认位） |
| `tools/比赛当天初始化.py` | `scripts/contest_init.py` |
| `比赛当天初始化.bat` | `START_WINDOWS.bat` |
| `一键启动提示词.txt` | 广告/微信号去除后，要点提炼进本文件与 README |

### 6. figure skill 去重移植 → `skills/academic-figure/`

- 上游在 `.agents/skills/academic-figure-skill` 与 `.claude/skills/academic-figure-skill`
  各有一份（内容重复）。**本仓库只保留一份**到 `skills/academic-figure/`。
- 该 skill 内部全部为自包含相对路径（`references/`、`assets/figures/`、`scripts/`），
  无需改路径。
- 体积 84.7MB，其中 `assets/figures/*/*.png|pdf` 已在 `.gitignore` 排除（Wave3 评估）；
  `assets/figure-atlas/`（13.1MB）作为 skill 运行所需保留。
- 保留其原始 `LICENSE`。

## 二、第三方版权声明处理

- v2.1 README 中含第三方小红书作者版权声明。**本仓库不继承该作者身份标识**，
  仅在此记录：“v2.1 含第三方作者版权声明，新仓库不继承其身份标识”。
- 获奖论文语料（729 篇 PDF）为用户本机只读外部资产，不入库、不随仓库分发。

## 三、风格参考

- `Ku-academic/` 仓库仅作结构与写法参考，未复制其任何文件。

## 四、Wave2B 新增上游来源

- `modules/deai-writing.md`：改编自通用去 AI 味 skill（六层诊断：观点/结构/表达/素材/叙事/情感），
  落到竞赛论文体裁，**未照抄原文**，仅借诊断框架与改写思路。
- `modules/solving.md` / `figures-interface.md`：在 Wave0 骨架上，按本文件"一.4"继续从 v2.1
  求解规范/绘图规范提炼充实，仍非原样复制。
- 官方规则依据：`_work/official_rules_research.md`（2025 格式规范、2026 AI 规定、评审四标准），
  含 URL 与检索日期 2026-09-20。
