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
| `华为杯_论文规范模板/page_targets.json` | 同名 | 页数门禁状态与历史观察（当前默认关闭） |
| `华为杯_论文规范模板/agent_manifest.schema.json` | 同名 | 论文清单 schema |
| `华为杯_论文规范模板/章节页数基线.json` | 同名 | 历史章节页数观察（不作目标或门禁） |
| `华为杯_论文规范模板/章节模板/` | `assets/paper-template/章节模板/` | 各章节 .tex 模板 |
| `华为杯_论文规范模板/figures/` | `assets/paper-template/figures/` | 论文图占位/logo |
| 第二十三届官方附件 3 Word 内嵌 `image1`–`image4` | `figures/identity-*` | 2026 正式提交第 0 页封皮的四个徽标 |
| `华为杯_论文规范模板/华为杯_论文章节规范.md` | 同名 | 章节规范 |
| v2.1 `研赛论文Word标准模板.docx` | 不再分发 | 经复核为旧社区写作稿，不是 2026 官方附件 3；曾含目录、占位正文与错误页边距，已从当前树删除 |

> 许可状态（逐资产）：`gmcm.bst` 的文件头表明其实际来源为 Zeping Lee 的
> `gbt7714-unsrt.bst`，明确允许按 LPPL 1.3c 或更高版本分发和修改；当前文件保留了完整版权与
> 许可头，重命名后的使用还应继续遵守 LPPL 条件。除此之外，截至 2026-09-23，
> `gmcmthesis.cls`、`gmcm-title.sty` 和四个徽标仍未找到可核验的再分发授权；
> 公开可见或允许 fork 不等于允许复制、分发或制作衍生物。本仓库的 MIT 许可不覆盖这些第三方
> 文件。旧社区 Word 二进制已从当前树删除；Word 派生工具只接受用户有权使用的本地模板。取得
> 剩余资产相应权利人明确授权前，不生成面向公众的预打包 Overleaf ZIP；保留此记录不代表授予任何权利。

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
- 当前第二十三届格式依据：`docs/OFFICIAL_FORMAT_2026.md`，由用户提供的三份官方 Word 文件核对；其优先级高于上述历史调研记录。

## 五、Wave6 新增上游来源（优秀论文自检表）

- **来源**：用户于 2026-09-21 提供的**第三方"优秀论文自检表"图片（7 张截图）**。
  图片带小红书水印，但**本仓库不记录水印账号 ID**（第三方资料，仅作经验参考，不继承其身份标识）。
- **处理**：7 张截图逐张转录为工作记录 `优秀论文自检表_原始转录.md`（本地 `_work/` 工作记录，已 gitignore 不入库），并固化为入库资产：
  - `assets/checklists/paper_checklist.json`（138 条结构化条目，机检用）
  - `assets/checklists/优秀论文自检表.md`（人读版，AI 相关措辞已中性化）
- **机检与门禁**：`scripts/paper_checklist.py` 仅自动判断可客观识别的结构项；需视觉或学术判断的条目保留人工裁决，P4/P6 门禁检查是否闭环而非强行全绿。
- **3 处转录存疑（已经用户确认定稿，notes 置空）**：
  - **M14**（预测模型评估）：原图此行被水印遮挡，按"分类模型评估（M11）"同构补全；定稿为"模型评估（讲如何控制输出）"。
  - **I02**（改进可否分点）：原图两条互相矛盾；定稿为"以整段写为主、可以分点但不能跑题"。
  - **V05**（误差检验）：当时按截图定稿为“误差检验优先使用五折交叉验证”；2026-09-21 的内容审计确认该说法不能跨 IID、分组、时序和空间数据通用，现已改为“验证划分服从数据结构”。这属于纠错，不抹去原始转录历史。
- **与官方规范的冲突（已按官方裁定）**：
  自检表 **F03** 原要求二三级标题"小四号**黑体**"；但华为杯官方 `华为杯_论文章节规范.md` §2.3(1)
  明确为"小四号**宋体**"，且禁止改 `gmcmthesis.cls`；`gmcmthesis.cls` 与 Word 模板现状均为宋体小四。
  经用户 2026-09-21 裁决：**以官方格式规范为准（小四宋体），第三方"黑体"不采纳，不改模板**，
  定稿记录在 `modules/paper-writing.md` §6.1 与 `docs/CHANGELOG.md` v0.4.1。

## 六、第二十三届社区 LaTeX 参考包

- **来源**：用户于 2026-09-21 提供的本机 PDF、`main.tex`、`gmcmthesis.cls`、`gmcm.bst`、`figures/logo.pdf` 与 `figures/title.pdf`。
- **身份判断**：`gmcmthesis.cls` 文件头注明由 `latexstudio.net` 创建并由社区作者更新；不能称为组委会官方 LaTeX 模板。
- **装载方式**：六个文件在用户本机 skill 中按 SHA-256 装载；公开仓库仅保存 `assets/paper-template/reference-23rd-latex/source-manifest.json` 与 `docs/TEMPLATE_CONTENT_MAPPING_23RD.md`。
- **分发边界**：源包未附明确再分发许可，故不把原 PDF、源文件或图像提交到公开 GitHub。
- **融合范围**：吸收任务卡、数据审计、Baseline—主模型证据链、按结构验证、不确定性、结果解释、模型评价、结论和复现元数据；拒绝目录、社区类文件、组合 logo 与写有“第二十二届”的过期标题资产。

## 七、figures4papers 作图来源审计与许可补救

- **来源**：[`ChenLiu-1996/figures4papers`](https://github.com/ChenLiu-1996/figures4papers)，锁定提交
  `3c181f85e82c6f24948fcaaf3be6696102b41d8d`，审计日期 2026-09-24。
- **许可**：上游根许可证为 CC BY-NC 4.0，并非 MIT/Apache。它要求署名、
  来源/许可链接和修改说明，并限制非商业用途；本仓库根 MIT 和
  `skills/academic-figure/LICENSE` 不重新许可这些内容。
- **现有重合补救**：审计发现 `skills/academic-figure/assets/figures/` 中有
  17 个文件与该锁定上游逐字节相同，另有 3 个改编文件。完整路径映射、
  修改状态和作者归属见 `skills/academic-figure/THIRD_PARTY_NOTICES.md`；
  完整许可证正文见 `skills/academic-figure/LICENSES/CC-BY-NC-4.0.txt`。
- **全量覆盖而非全量复制**：95 个树条目中的 76 个文件已全部登记在
  `skills/academic-figure/references/figures4papers.lock.json`。25 个 Python、
  39 张 PNG、3 个 PDF、7 个 Markdown 及其余许可/配置文件均有明确
  disposition。PNG/PDF、论文数据和复合 raster 默认为 reference-only，不再复制。
- **融合方式**：通用图形思想以独立表述写入
  `skills/academic-figure/references/figures4papers-profile.md`；对截断柱轴、
  红绿唯一编码、alpha-only 分类、逐列热图误读、跨量纲雷达面积、超宽画布、
  硬依赖 Helvetica/TeX、导入即出图等做了拒绝或安全改造。商业或用途不清时
  只能从零实现通用原则，不能调用 CC BY-NC 模板。
- **独立 Skill 分发**：上游真实 `scientific-figure-making/` 现以独立目录
  `skills/scientific-figure-making/` 随仓库分发，不与 `academic-figure` 合并。
  其 `SKILL.md`、五份 reference 和完整许可证继续适用 CC BY-NC 4.0；根 MIT
  与 `academic-figure` 的 Apache-2.0 均不重许可这些内容。修改仅包括：在
  `SKILL.md` 增加本仓许可/科学安全画像的优先路由；把 `demos.md` 的移动
  `tree/main` 链接锁到提交 `3c181f85e82c6f24948fcaaf3be6696102b41d8d`；
  增加 `SOURCE.md` 与 `agents/openai.yaml` 集成元数据。逐文件 blob 与修改说明
  见该目录的 `SOURCE.md`，并继续由 figures4papers 锁文件和测试覆盖。
