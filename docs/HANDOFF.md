# huawei-mcm 深化交接包（给 GPT / 下一位优化者）

> 本文件用于把"华为杯中国研究生数学建模竞赛 AI 作战中枢"（仓库名 **Huaweibei-cool**，skill 名 **huawei-mcm**，当前版本 **v0.4.1**）无缝交给下一位 AI/开发者继续深化。
> 写作日期：2026-09-20。交接对象：GPT（或任何 Agent）。
> 阅读顺序：第 0 节宣传物料 → 第 2 节全部路径 → 第 4 节仓库结构 → 第 6 节全部已知局限 → 第 7 节优化路线图 → 第 8 节红线。

---

## 0. Skill 定位与宣传物料

### 0.1 一句话定位

把 2004–2024 年 **729 篇华为杯获奖论文**与 2022–2025 赛题解析，蒸馏成一个带"反套路读题硬门禁 + 题型原型方法库 + 比赛日全流程脚本 + LaTeX/Word 双论文链路 + 质量门禁"的 **AI 作战中枢**。**它不替人解题、不承诺获奖、不代提交**，只把获奖队伍的工作流、避坑点和工程纪律固化下来。

### 0.2 广告语（可直接用于 README / 社媒 / 海报，已去除旧品牌字样，不承诺获奖）

- **主标题（横幅用）**：华为杯研赛 · AI 作战中枢
- **副标题（横幅用）**：729 篇获奖论文蒸馏 · 八大题型原型 · 从读题到提交全程护航
- **口号（横幅/水印用）**：读懂题 · 建对模 · 写好论文 · 稳交卷
- **主标语 A**：把 729 篇获奖论文，变成你的 4 天 3 夜 AI 作战中枢。
- **主标语 B**：别人在套模板，你在逐句读题、证据建模、步步为营。
- **主标语 C**：从第一句题面到最后一页论文，每一步都有门禁、有证据、有复盘。
- **GitHub About 短介绍（推荐直接填）**：华为杯中国研究生数学建模竞赛 AI 作战中枢：729 篇获奖论文蒸馏 · 8 大题型原型 51 张方法卡 · 2022–2025 共 24 题赛道档案 · 反套路读题人工确认门禁 · LaTeX/Word 双论文链路 · 全流程质量测试。
- **免责语（凡宣传处必须同框出现，合规红线）**：本工具不承诺获奖、不代提交；AI 仅作辅助，须按当届官方规定披露使用情况。

### 0.3 宣传图片

- 文件：**`huawei-mcm-banner.png`**（与本交接包同目录，1920×1080，约 737KB），深藏青蓝底 + 金/青线条，含公式、三维曲面、网络图、数据图表、齿轮流程、雷达波纹元素；图上文字为"华为杯研赛 · AI 作战中枢 / 729篇获奖论文蒸馏 · 八大题型原型 · 从读题到提交全程护航 / 读懂题 · 建对模 · 写好论文 · 稳交卷"，**无旧品牌字样、无人名机构**。
- README 嵌入：`![huawei-mcm](docs/banner.png)`（AI 生成、无校徽商标）。
- 再生提示词（存档，便于出变体）：
  > 高端学术科技风横版横幅，深藏青蓝到墨黑渐变背景，金色与青色线条光效；半透明数学公式（积分、矩阵、偏微分方程）、三维曲面图、网络节点图、数据图表、齿轮算法流程图、隐约雷达波纹；金色粗体中文大标题"华为杯研赛 · AI 作战中枢"，白色副标题"729篇获奖论文蒸馏 · 八大题型原型 · 从读题到提交全程护航"，底部青色小字"读懂题 · 建对模 · 写好论文 · 稳交卷"；印刷级质感，无卡通、无人物、无校徽商标，文字清晰无错别字。

---

## 1. 项目背景

- 使用者画像：主力语言 MATLAB（MATLAB 为一等求解器，Python 为默认胶水链），熟悉大规模数据处理与论文出图流水线。
- 目标：做一个高竞争力、工程严谨的华为杯中国研究生数学建模竞赛全流程 Skill，风格对标成熟 Skill 仓库 **Ku-academic**（根 SKILL.md 路由 + modules 任务契约 + scripts 硬门禁 + docs + tests）。
- 知识来源：
  1. 2004–2024 获奖论文 729 篇 PDF（2.26GB）；
  2. 2022–2025 赛题解析资料 1368 个文件（29GB，含 49 个 mp4 约 18GB）；
  3. 用户自有的比赛日工程包 v2.1（huawei_skillsv2_v2.1_competition_ready.zip）；
  4. 官方规则联网调研（格式规范、2026 AI 使用规定）。
- 用户的两条最高优先级要求：
  - **读题审计必须"反 AI"**：出题组会反套路命题；必须逐句逐段拆解、列出任务/模型/图表大纲，**先给用户判断、等明确确认后才允许求解**，"千万不要聪明反被聪明误"。
  - **反复检查迭代、确认各步骤无误后才允许 git commit/push**。

---

## 2. 全部文件与路径清单（重要）

### 2.1 产物仓库与安装

| 项 | 路径 / URL |
|---|---|
| 目标仓库（工作副本，所有产物落地处） | `C:\Users\ASUS\Doubao\chats\2026-09-20\new-chat-12\Huaweibei-cool` |
| GitHub 远端 | 仓库自身的 `origin`（仓库名 Huaweibei-cool；公开文档中不写含真实姓名拼音的完整 URL） |
| 已安装 junction（Doubao 发现入口） | `C:\Users\ASUS\Doubao\skills\huawei-mcm` → 仓库根 |
| 分支 / 最新 commit | `main`；v0.1.1 = `a68b9fb`（远端已同步，upstream 已配） |
| 交付说明 | 仓库根 `交付说明.md` |

### 2.2 输入语料（**只读红线：禁止移动/删除/回写/重命名**）

| 语料 | 路径 |
|---|---|
| 获奖论文根（729 PDF，21 个年份文件夹，2.26GB） | `C:\Users\ASUS\Desktop\26华为杯研赛1\②历年获奖作品（04-24年）\中国研究生数学建模竞赛优秀论文\` |
| 赛题解析根（1368 文件，29GB） | `C:\Users\ASUS\Desktop\26华为杯研赛1\④赛题解析（22-25年）\` |
| ├ 2022 思路 | `22华为杯研究生数模思路\会员专享\`、`22华为杯研究生数模思路\免费思路资料\` |
| ├ 2023 思路代码（仅 C–F，**A/B 缺失**） | `23年研究生建模思路代码\C` … `F` |
| ├ 2024 思路代码（A–F，部分思路 PDF 为扫描件） | `24年研究生建模思路代码\A` … `F` |
| └ 2025 思路代码（渠道一含论文模版/AI提示词/冲刺资料 306 文件；渠道二） | `25华为杯研赛思路代码\渠道一\`、`渠道二\` |
| v2.1 工程包 zip 原件 | 本机微信文件接收目录（xwechat_files）下 `2026-09\huawei_skillsv2_v2.1_competition_ready.zip`（路径含账号标识，公开文档不写全） |
| v2.1 解压目录 | `C:\Users\ASUS\Doubao\chats\2026-09-20\new-chat-12\zip_extract\huawei_skillsv2_v2.1_competition_ready` |
| 风格标杆仓库（已 clone） | `C:\Users\ASUS\Doubao\chats\2026-09-20\new-chat-12\Ku-academic` |

### 2.3 构建过程中读过的 Skill（方法论来源，深化时按需重读）

skill 根：`C:\Users\ASUS\AppData\Local\Doubao\User Data\Profile 1\.doubao\agent_mode\workspace\.skills\`

| skill | 相对路径 | 用途 |
|---|---|---|
| skill-creator-for-work | `skill-creator-for-work\SKILL.md` | skill 写法（frontmatter 仅 name/description、SKILL.md ≤500 行、渐进式加载、scripts/references/assets 分工） |
| doubao-human-signal（去 AI 味） | `doubao-human-signal\SKILL.md` | 改编为 `modules/deai-writing.md`，**不得照抄全文**，来源见 `docs/UPSTREAM.md`；其 references/ 细则未全读，深化前应重读 |
| doubao-pdf | `doubao-pdf\SKILL.md` | PyMuPDF 抽文/渲染、扫描件 PNG 多模态读、表格抽取与质检 |
| doubao-academic-researcher | `doubao-academic-researcher\SKILL.md` | 证据双轴分级、引用核验、门禁-回退思想；完整内容未读全，深化前重读 |

### 2.4 仓库内关键路径

- `SKILL.md`（79 行，frontmatter `name: huawei-mcm`；五入口路由 A 赛前训练 / B 比赛日全流程 / C 单题卡点 / D 论文打磨 / E 赛后蒸馏；P0–P6 阶段契约；9 条硬规则）
- `modules/`（20 个，见 4.2）
- `playbooks/`（8 原型 + `INDEX.md` + `match_rules.json` 13 条规则 + 51 张方法卡）
- `tracks/`（README + 选题统计 + `2022/…/2025/A.md…F.md` 共 24 份）
- `corpus/`：`papers_index.json/.csv`（729 条）、`schemas/`（brief/deep/playbook/track 四个 JSON Schema）、`cards/brief/`（21 个分片文件含 729 简卡）、`cards/deep/`（80 张深卡 JSON）、`problem_analysis/`（S5 赛题解析蒸馏 32 文件）、`CORPUS_NOTES.md`、统计文件
- `scripts/`（18 个 .py + `render_word.vbs` + `视觉计划.schema.json`）
- `tests/`（8 文件，25 用例）
- `docs/`（9 份，见 4.3）
- `assets/paper-template/`（gmcmthesis.cls / gmcm.bst / gmcm-title.sty / example.tex / reference.bib / 章节模板 / Word 模板 / page_targets 等）
- `assets/scaffold/`（比赛日五区空骨架）
- `skills/academic-figure/`（v2.1 配图子 skill，去重后单份，146 个文件，含 19 张参考 PNG 约 13MB）
- `config/contest.json` + `contest.schema.json`
- **本地独有、不入库（.gitignore 已排除）**：
  - `corpus/text/`：729 个抽文 txt + `_rendered/` 乱码论文渲染 PNG；
  - `_work/`：`latex_build/example.pdf`（12 页编译实证）、`dryrun/`（全链路 dry-run）、各类探针与一次性补丁脚本（`sanitize_titles.py`、`patch_*.py`）。

### 2.5 环境

- Windows 11 + 完全访问模式；Python **3.14.7**（PyMuPDF 1.28.2、pypdf 6.19.0、python-docx、pytest 已装）；git 2.54；**XeLaTeX（TeXLive 2026）可用**；**本机未安装 MATLAB**（MATLAB 链路未真机验证）。
- 官方规则 URL（2026-09-20 检索，**每届必须重新核对**）：格式规范 `https://www.cmathc.org.cn/mcm/tz/317.html`；AI 使用规定 `https://www.cmathc.org.cn/cpmcm/news/643.html`。

---

## 3. 当前已验证状态（v0.1.1，勿重复声称"已验证"除非重跑）

- `python -m pytest tests/ -q` → **25 passed**（索引完整性、729 简卡 + 80 深卡 schema 零违例、P0–P2 门禁正反例、**P1 用户确认门禁正反例**、playbook_match、submission_audit、audit_tex、figure 中文字体烟雾）。
- 18 个 .py 脚本 `--help` 全部退出码 0；`corpus_cards.py --stats` 可复现（briefs=729 / deeps=80 / methods=67）。
- `playbook_match.py` 对 2024 A 题面：主原型 optimization=0.99。
- `progress.py --gate P1` 实测：无 `evidence-ledger` 用户确认记录时 **FAIL**（即使其他 P1 产物齐全），有确认记录时 PASS。
- XeLaTeX 双遍编译 example.tex 成功（放占位 loglo.png 后，12 页 PDF）。
- `contest_init.py` dry-run 全链路跑通。
- git：481 个跟踪文件，PDF/txt/视频/`_work` 均被忽略；3 个 commit 已推送。
- 赛道分布（最终索引口径）：A=121 / B=134 / C=104 / D=126 / E=89 / F=77 / 空=78（空值集中在 2004–2006 中文描述性命名）。

---

## 4. 仓库结构与模块职责

### 4.1 根文件

`SKILL.md`、`README.md`、`AGENTS.md`、`CLAUDE.md`（镜像）、`START_WINDOWS.bat`、`LICENSE`(MIT)、`requirements.txt`、`.gitignore`、`交付说明.md`。

### 4.2 modules/ 20 个任务契约

| 文件 | 职责 |
|---|---|
| workflow.md | 比赛日 72h 时间线与阶段交接 |
| phases.md | P0–P6 阶段契约详表（内容级门禁） |
| **kickoff-audit.md** | **反 AI 读题审计（核心）**：7 类陷阱清单、逐段四元组（原文/复述/约束 Cx/歧义 Qx）、7 节审计报告、人工确认 P1 硬门禁、官方规则核对表 |
| track-selection.md | 选题决策（字母按届重置警告） |
| problem-typing.md | 题面→8 原型匹配；**判型只产候选，质证前不采信** |
| solving.md | 求解主线：假设→建模→算法→结果 |
| validation.md | 验证门禁：误差/对比/灵敏度/消融 |
| evidence-ledger.md | 证据台账与 AI 来源标注 |
| figures-interface.md | 论文图规范与求解图接口；图表计划必须源自读题审计报告 |
| paper-writing.md | 章节结构、内容密度与官方页数限制核对（当前默认无页数门禁） |
| abstract.md | 摘要专项（国一模板；官方表述为摘要一般不超过两页） |
| deai-writing.md | 反模板/反 AI 味（源自 human-signal，需继续吸收其 references） |
| innovation.md | 创新点提炼与伪创新识别 |
| submission.md | 提交规范与 AI 披露（2026 规定） |
| review-panel.md | 评审团模拟自评 |
| polishing.md | 打磨审校与数字一致性 |
| change-management.md | 比赛中变更管理与回退 |
| distillation.md | 赛后蒸馏与方法卡沉淀 |
| matlab-conventions.md | MATLAB 工程规范（**未真机验证**） |
| training.md | 赛前训练计划 |

### 4.3 docs/ 9 份

`ARCHITECTURE.md`、`PHASE_GATES.md`、`ACCEPTANCE.md`、`SCORING_RUBRIC.md`（官方四维度=假设合理性/建模创造性/结果正确性/文字表述清晰度；细则为经验推断，已标注）、`DISTILLATION_METHOD.md`（含留出盲检结果）、`PEER_COMPARISON.md`、`CHANGELOG.md`、`TRACK_ARCHIVE_2004_2021.md`、`UPSTREAM.md`（v2.1 与第三方模板来源、许可）。

### 4.4 scripts/（18 .py）

`contest_init.py`（五区骨架）、`corpus_build.py`（抽文/索引）、`corpus_cards.py`（聚合统计/同义词归一/原型触发）、`playbook_match.py`、`progress.py`（P0–P6 内容级门禁，`--root/--gate/--all/--json`）、`evidence.py`、`review.py`（启发式打分，**非真评审**）、`submission_audit.py`、`visual_plan_init.py`、`visual_plan_audit.py`、`build_latex.py`、`audit_tex.py`、`audit_paper.py`、`build_docx.py`、`audit_docx.py`、`migrate_markdown_to_tex.py`、`calibrate_page_targets.py`、`blind_check.py`；外加 `render_word.vbs`、`视觉计划.schema.json`。

---

## 5. 语料处理口径（事实底稿）

- 729 篇全部 PyMuPDF 抽文成功（最小 1993 字、中位约 61900 字、最大 251958 字），无扫描件失败；个别 CID 字体乱码论文已渲染 PNG 视觉补读或标 low 置信。
- 简卡字段：问题数/任务类型/模型算法清单/数据模态/验证手段/创新点/章节结构/页码定位；深卡另含逐问方法链、摘要拆解、高分理由、精确页码。
- 深卡 80 张分布：2024 年 24 张全覆盖、2021 年 18 张（含 12 篇数模之星提名）、2014/2022 各 5、2017/2018 各 3，其余年份 1–2。
- 证据分级 A/B/C：获奖论文为 A/B，2025 商业思路资料全部 C。
- 引用格式：`[年-赛道-paper_id-页码]`；Wave2A 时 72 个被引 paper_id 校验零缺失。
- 已核实赛题主题举例：2022（A FMCW 雷达超分辨定位 / B 二维排样 / C PBS 调度 / D 芯片排布 / E 草原放牧 / F 疫情物资）；2023（C 竞赛评审 / D 双碳路径 / E 脑卒中预测 / F 强对流预报；A=WLAN 信道建模、B=DFT 矩阵分解，由获奖简卡反推）；2025（A 图计算内存预算 / B MIMO 链路级仿真 EESM / C 围岩裂隙识别三维重构 / D 风廓线雷达·微波辐射计反演 / E 轴承故障诊断 / F 医学影像分割）。

---

## 6. 全部已知局限（深化的问题清单，不得洗白）

### A. 工程与环境

1. **MATLAB 互操作未真机跑通**：本机无 MATLAB，`matlab-conventions.md` 仅规范约定；`.m` 求解器链路（fmincon/intlinprog/ga/ode45 等）未实测。
2. **模板缺 `loglo.png`（v2.1 上游笔误）**：`example.tex` 引用了不存在的 `loglo.png`，干净机器首次 xelatex 编译在 xdvipdfmx 阶段失败；本次靠 `_work/latex_build/` 占位图编译通过（12 页）。需在模板里修正引用或随仓库提供合规占位图。
3. **bibtex 无引用告警**：模板示例正文无 `\cite`，bibtex 提示无引用——属正常现象，文档已说明。
4. **Word 链路 `render_word.vbs` 仅 Windows**，未在干净机器做端到端烟雾。
5. **requirements 未严格锁版本**；无 CI（建议加 GitHub Actions：Windows + Python 3.14 跑 pytest）。
6. figure-atlas 19 张 PNG 约 13MB 已入库（低于 50MB 阈值），如需瘦身可改为 LFS 或外链。
7. `review.py` 是启发式打分，不是真评审，措辞已声明；阈值未经历史论文回测标定。

### B. 语料与元数据

8. **奖级大面积未知**：索引中 722/729 标"待确认"（仅 7 篇首页正则命中一等奖）；`CORPUS_NOTES.md` 另一处口径为 615/729（84.4%）。**两个数字未对账，需先核对统计口径再统一**；理想方案是渲染封面/证书页做多模态奖级识别。
9. **2014/2015 串号**：2014 文件夹嵌套"2015年"子目录，53 篇实为第十二届（2015）论文；索引以 year 字段归类并在 notes 记录，早年主题速查仅供参考。
10. **2023 A/B 商业思路缺失**：现档案由获奖简卡反推（A=WLAN 信道建模 10 篇、B=DFT 矩阵分解 9 篇），证据厚度低于其他题。
11. **2024 每题仅 4 篇样本**（共 24），单题方法谱系置信度低。
12. **2025 档案全部 C 级证据**（商业思路/AI 提示词包），无获奖论文；官方题面发布后需升级证据。
13. **2022/2024 部分思路 PDF 是扫描件**，未 OCR。
14. **49 个 mp4（约 18GB）讲解视频未转写**。
15. **乱码/低置信卡片**：S2 有 4 篇 CID 字体乱码标 low 置信；S3 有 3 篇已渲染视觉补读；需复核是否还有遗漏。
16. **早期论文无摘要**：2004–2012 多数无规范摘要，简卡 models_and_algorithms 稀疏，方法频次被系统性低估。
17. **通用标签污染**：60 张简卡的 models_and_algorithms 含"禁忌搜索/启发式"泛化标签（并非真用禁忌搜索），已在 AGGREGATE_STATS 标注，待逐条清洗。
18. **标题启发式粗糙**：部分早期论文标题取成正文首句（如 2005 出租车题）；v0.1.1 已清洗 81 条广告水印标题（"有偿…加微 anjia…"），但其余低质量标题仍在（置信度 low 是设计使然）。
19. **抽文 txt 仍含水印文本**：txt 不入库（.gitignore），若未来要分发语料文本，需先做全文水印清洗。
20. 截至 2026-09-21，当届已核对的官方材料未规定正文/全文页数上限；`contest.json` 默认关闭页数门禁。每届仍须重查赛题与后续通知，只有明确上限时才启用。

### C. 知识与判型

21. **盲检样本不足且命中率一般**：仅 2023 年 10 篇留出盲检，判型对齐 4/10=40%（其中 1 条双方都 unknown，有效命中约 3–4/9）。已定位三类问题：
    - "仿真验证"过度触发 simulation（WLAN 两例本质是 Markov/机理建模）——match_rules 缺"Markov 链/通信协议/信道"机理触发词；
    - 评价题（评审/方案比较）误判 optimization——需补 evaluation 触发词；
    - 关键词粗筛对"用仿真做验证的解析题"系统性误判，人工复核不可省。
22. **深卡覆盖率仅 80/729 ≈ 11%**，2015–2020 与 E/F 轨偏薄。
23. 方法频次基于 67 个同义词归一类，归一表未经第二人审计，可能有合并/拆分偏差。
24. S5 提炼的 45 个组合模型方法卡与 playbooks 的交叉链接是否完整，需复查。
25. `SCORING_RUBRIC.md` 四维度来自官方公开信息，但评分细则锚点为经验推断；需继续找高校研院/竞赛办公开评审文件并标注 URL 与检索日期。

### D. 合规与版权

26. 第三方模板 `gmcmthesis.cls`/`gmcm.bst`/`gmcm-title.sty` 依赖系统字体 **STXinwei** 与 XeLaTeX，许可与出处保留在 `docs/UPSTREAM.md`；**v2.1 README 中第三方小红书作者声明不得带入本仓库**（已排除，后续合并上游时继续拦截）。
27. AI 披露条款依据 2026 规定，2027 届及以后必须重新核对官方页面。
28. Skill 中"国一"字样是目标品牌不是承诺；所有对外宣传必须带免责语（见 0.2）。

---

## 7. 深化优化路线图（建议按优先级）

### P0——比赛日前必须做

1. **MATLAB 真机链路**：在装有 MATLAB 的机器上验证 CLI/batch 调用、fmincon/intlinprog/ga/ode45 最小示例、与 Python 数据交换（.mat/CSV）、中文出图字体；把结果回写 `matlab-conventions.md` 与 tests（无可跳过标记为 live-validated pending）。
2. **修掉 loglo.png**：改 `example.tex` 引用或提供合规占位图；在干净目录重跑双遍编译 + `audit_paper.py` 并截图存档。
3. **扩大留出盲检并修 match_rules**：分层抽 2022–2024 至少 30 题（8 原型各有代表、含"仿真验证的解析题"与"评审/方案比较题"）；补触发词（Markov 链/通信协议/信道→mechanism；评审/方案比较/综合评价→evaluation；仿真仅作验证手段时不单独触发 simulation）；记录每类精确率/召回率，写回 `docs/DISTILLATION_METHOD.md`；新增对应 pytest 正反例。
4. **端到端实战彩排**：选一道历史题（建议 2024A 优化题，或 2025E 轴承故障诊断以发挥 MATLAB/信号处理优势）完整走 P0–P6：读题审计报告（人工确认）→ 判型 → 求解 → 视觉计划 → 论文骨架 → 全部门禁；把摩擦点回填模块。
5. **奖级口径对账 + 多模态识别**：先核对 615 vs 722 的统计差异；再用封面/证书页渲染图做奖级识别，回填索引与卡片，重算统计。

### P1——显著提升知识厚度

6. OCR 2022/2024 扫描版思路 PDF（PyMuPDF 渲染 + 多模态读或 Tesseract），补齐 tracks 档案。
7. 转写 49 个 mp4（ASR/Whisper 类方案），提炼后入 `corpus/problem_analysis/`，原视频不入库。
8. 清洗 60 张泛化标签简卡；审计同义词归一表；`corpus_cards.py --stats` 重算并核对差异。
9. 深卡从 80 扩到 ≥150：按年份×赛道×原型分层补 2015–2020 与 E/F 轨。
10. 用获奖简卡把 2023 A/B 档案补到与其他题同厚度；2025 官方材料发布后升级证据等级。
11. 改进早期论文标题提取（结合文件名、封面视觉、摘要首句）。
12. 给 `corpus/text` 增加"分发前水印清洗"脚本（默认不跑、不改正文抽取流程）。

### P2——工程化与体验

13. GitHub Actions（Windows + Python 3.14）跑 pytest 与脚本 `--help`；锁 requirements。
14. `review.py` 用 SCORING_RUBRIC 锚点回测标定，输出四维度分项与改进建议。
15. 配图体系：配色 token 化（期刊审美 + 色盲友好 + 黑白可分）、自动色盲检查、扩充 figure-atlas 模板。
16. `deai-writing.md` 吸收 doubao-human-signal 的 references 细则，配真实语料 before/after 对照。
17. Word 链路在干净 Windows 上跑 `render_word.vbs` 端到端。
18. 补"可复现性文档"：每条产物的重算命令、输入哈希、预期输出。
19. 社媒发布时使用第 0 节广告语 + banner，仓库 About 填短介绍。

---

## 8. 红线与验收标准（不可违反）

1. **语料只读**：Desktop 两个语料根的任何文件不得删除/移动/重命名/回写；PDF、全文 txt、视频、压缩包一律不入 git（.gitignore 已配，改动后复查）。
2. **禁伪造**：数字、方法归属、实验结果、引用来源不得编造；拿不准标"待确认"+置信度；统计必须可由脚本重算。
3. **P1 人工确认硬门禁不可绕过**：读题审计报告未呈现给用户、未拿到明确确认记录（evidence-ledger `user_confirmation=true`）前，禁止进入求解；时间紧只许压缩篇幅，不许取消门禁。
4. **判型只产候选**：playbook_match 结果必须经题面约束（Cx 编号）逐条质证；无证据的建模选择标"待论证"。
5. **广告零容忍**：标题、卡片、模块、文档中不得出现微信号/代写/代充等广告文本；新增语料处理必须过广告正则（v0.1.1 已在 `corpus_build.py` 加标题过滤）。
6. **合规**：按当届官方规定做 AI 使用披露（工具名/版本/机构/日期）；无来源模型公式不写；skill 不承诺获奖、不代提交、不鼓励抄袭。
7. **第三方资产**：模板许可与来源记录在 `docs/UPSTREAM.md`；v2.1 的第三方作者宣传内容不得带入。
8. **Skill 规范**：SKILL.md frontmatter 仅 `name`/`description`（当前 `name: huawei-mcm`），正文 ≤500 行（当前 79）；细节放 modules/docs，避免重复。
9. **验证纪律**：所有脚本在 Windows Python 3.14 实跑；知识产物改动后重跑 `corpus_cards.py --stats` 核对；**`pytest` 全绿 + 关键命令人工抽查通过后才 commit/push**；push 后用 `git ls-remote origin` 核对远端 SHA。
10. **完成报告三态**：implemented / tested / live-validated pending，不得把"写完"说成"跑通"。

---

## 9. 常用命令速查（仓库根目录执行）

```powershell
# 环境
python --version; git --version; xelatex --version

# 测试
python -m pytest tests/ -v

# 语料（默认路径写死在脚本，可 --corpus-root 覆盖；语料只读）
python scripts/corpus_build.py                 # 断点续跑重建索引（读 txt，很快）
python scripts/corpus_build.py --rescan        # 强制重新抽文（729 篇，约 8 分钟）
python scripts/corpus_cards.py --stats         # 重算方法频次/赛道原型矩阵

# 比赛日
python scripts/contest_init.py --workdir <工作目录>
python scripts/playbook_match.py --txt <工作目录>\题目\题面.txt   # 仅候选
# 按 modules/kickoff-audit.md 产出读题审计报告 → 用户确认 → 写 evidence-ledger
python scripts/progress.py --root <工作目录> --gate P1
python scripts/progress.py --root <工作目录> --all
python scripts/visual_plan_init.py ...         # 图表计划
python scripts/build_latex.py ...              # LaTeX 双遍编译
python scripts/submission_audit.py --paper <终稿.pdf>

# git
git status -sb; git add -A; git commit -m "..."; git push
git ls-remote origin refs/heads/main           # 核对远端
```

---

## 10. 给 GPT 的工作方式要求

- 先通读 `SKILL.md` → `modules/kickoff-audit.md` → `docs/PHASE_GATES.md` → `docs/ACCEPTANCE.md` → `交付说明.md` → 本文件，再动手。
- 保持 Ku-academic 式的紧凑模块写法："目标声明 → 操作规则 → schema/字段 → 检验 → 边界"，不写空话。
- 用户的原话精神：**"千万不要聪明反被聪明误"**——宁可慢、宁可多问、宁可把不确定性摆上台面，也不许抢跑下结论。
- 每改一处知识产物，说明证据来源与等级；每改一处脚本，补/改测试并实跑；每一轮收尾给出三态报告与未验证项。
- 用户主力是 MATLAB：深化时把 MATLAB 当一等求解器（Python 仍是默认胶水链），代码片段要可在 MATLAB 中直接运行。
- 中文交付。

（完）
