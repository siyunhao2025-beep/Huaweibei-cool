---
name: huawei-mcm
description: 华为杯（中国研究生数学建模竞赛）AI 作战中枢。覆盖赛前训练、比赛日全流程、单题卡点求助、论文打磨、赛后蒸馏五类场景。当用户要准备或参加华为杯研赛、需要按获奖论文范式建模/求解/写论文、或要对一道赛题做方法选型与论文成稿时触发。不用于普通课程作业、非数学建模的科研论文、或纯绘图需求（绘图走 academic-figure 子 skill）。
---

# Huaweibei-cool · 华为杯研赛 AI 作战中枢

以 2004–2024 共 729 篇获奖论文语料为底座，把"建模—求解—论文—打磨—赛后蒸馏"
固化成 21 个任务契约模块、8 原型 51 张方法卡、24 题赛道档案与一组门禁脚本。
知识库蒸馏方法与已知局限见 `docs/DISTILLATION_METHOD.md`。

## 0. 首次使用钩子

当用户说“第一次使用”“怎么开始”“不会用”，或尚未提供可判断任务阶段的上下文时，先输出以 `✅` 开头的首次引导，不要直接倾倒模块、脚本或长清单。

固定执行：

1. 先提供或解析首次信息卡：学校、参赛队号、三名队员姓名、题号 A–F、当前阶段、已有文件、截止时间。允许暂缺；题号未定时进入选题比较，不得强迫用户猜题号。
2. 把学校、队号和姓名视为仅供第 0 页封皮使用的身份字段。首次响应只报告这些字段“已收齐/待补”，不要回显具体值；不得写入摘要、正文、图表或参考文献。
3. 从赛前、选题、建模、写作、终审五个阶段中判断当前阶段；仍不能判断时只问一个阶段问题。
4. 只索取当前推进所必需的材料，最多三类，例如题面、数据、现有代码/论文；不要求用户一次交齐全流程文件。
5. 返回“参赛信息状态、当前阶段、所需材料、下一步三件事、官方风险提醒”五项短结果。
6. 2026 终审或上传场景必须提醒：正式 PDF 首页是含团队信息的官方封皮，第二页起匿名；不能上传纯匿名摘要稿代替正式 PDF。

可提示用户复制：

```text
使用 $huawei-mcm。我是第一次使用华为杯 skill；请根据下面的信息开始首次引导。

1. 你的学校是：
2. 参赛队号是：
3. 队员姓名：
   - 队员 1：
   - 队员 2：
   - 队员 3：
4. 你选择的题目是：A / B / C / D / E / F / 未定
5. 当前阶段：赛前 / 选题 / 建模 / 写作 / 终审
6. 已有文件：题面 / 数据 / 代码 / 论文 / 暂无
7. 截止时间：
```

### 0.1 启动选择题路由

用户进入后，先按意图选一条主路（不要一次全跑）：

| 选项 | 场景 | 进入模块 |
|---|---|---|
| A | 赛前训练：刷题、方法体系、模拟赛 | `modules/training.md` |
| B | 比赛日全流程：题面到提交 | `modules/workflow.md` + `modules/phases.md`，先跑 `scripts/contest_init.py` |
| C | 单题卡点：某问建模/求解卡住 | **先过读题审计**（`modules/kickoff-audit.md`），再 `modules/solving.md` + `modules/validation.md` |
| D | 论文写作/打磨：正文骨架、成稿、排版、审校 | `modules/paper-writing.md` + `modules/polishing.md` + `modules/figures-interface.md`；涉及模板内容时再读 `docs/TEMPLATE_CONTENT_MAPPING_23RD.md` |
| E | 赛后蒸馏：复盘、方法卡沉淀 | `modules/distillation.md` |

## 1. 模块路由表（全部已完成）

| 模块 | 职责 |
|---|---|
| `modules/workflow.md` | 比赛日 72h 全流程时间线与阶段交接 |
| `modules/phases.md` | P0–P6 阶段契约详表（内容级门禁） |
| `modules/kickoff-audit.md` | 反 AI 读题审计：陷阱清单/逐段拆解/审计报告/用户确认门禁 + 规则/数据/环境 |
| `modules/track-selection.md` | 选题决策（字母按届重置） |
| `modules/problem-typing.md` | 题面→8 原型匹配流程 |
| `modules/solving.md` | 求解主线：读题→假设→建模→算法→结果；证据型策略选择 |
| `modules/validation.md` | 验证门禁：公平对比/误差/灵敏度/按风险配置证据，消融仅在适用时执行 |
| `modules/evidence-ledger.md` | 证据账本与 AI 来源标注 |
| `modules/figures-interface.md` | 论文图表证据组合、求解图接口、三线表与基线—候选对比图 |
| `modules/technical-roadmap.md` | 技术路线图（论文图1）：YAML 规格 + 8 原型模板 + 渲染/审计脚本 |
| `modules/paper-writing.md` | 论文章节结构、内容密度与官方页数限制核对；**138 条优秀论文自检表按单一来源逐章闭环**（F03 二三级标题字体已按官方规范裁决为小四宋体，见 §6.1） |
| `modules/abstract.md` | 摘要写法专项（高质量竞赛摘要结构） |
| `modules/deai-writing.md` | 反模板/反 AI 味写作 |
| `modules/innovation.md` | 创新点提炼与伪创新识别 |
| `modules/submission.md` | 提交规范与 AI 披露 |
| `modules/review-panel.md` | 评审团模拟自评 |
| `modules/polishing.md` | 打磨审校与数字一致性 |
| `modules/change-management.md` | 比赛中变更管理与回退 |
| `modules/distillation.md` | 赛后蒸馏与方法卡沉淀 |
| `modules/matlab-conventions.md` | MATLAB 工程规范 |
| `modules/training.md` | 赛前训练计划 |

## 2. 阶段契约 P0–P6 一览

| 阶段 | 名称 | 必做产物 | 门禁 |
|---|---|---|---|
| P0 | 环境初始化 | 目录骨架、contest.json | 题面/规则落盘 |
| P1 | 读题与拆解 | 逐段拆解、读题审计报告、题型候选、逐图清单 | **读题审计与 Figure 建议总数均经用户明确确认（确认记录写入 evidence-ledger 与视觉计划）** |
| P2 | 建模 | 假设≥3、模型链、基线 | 基线跑通 |
| P3 | 求解 | 代码、结果、验证、锁定数量的 Figure | 可复现+≥1验证；Figure 总数与用户锁定值一致；有候选改进时已完成策略选择 |
| P4 | 论文初稿 | 摘要/正文/结论、用户篇幅裁决 | 章节齐、摘要一般不超过2页、用户已选择总页数或“证据充分即可”、自检表文件就位 |
| P5 | 打磨审校 | 终稿、封皮后匿名化、引用 | audit 脚本 PASS；反 AI 味人工清单闭环 |
| P6 | 提交蒸馏 | 提交包、AI披露、复盘 | 提交审计 PASS + 自检表已勾选 + sidecar 无未裁决 |

详细工程化检查命令见 `docs/PHASE_GATES.md`。

## 3. 硬规则（不可覆盖）

1. **题面优先**：一切以当届官方题面与官方规则为准；本仓库经验值只在官方未规定时兜底。
2. **反 AI 读题（硬门禁）**：出题组会"反 AI"命题（诱导套路/隐藏约束/歧义陷阱）。
   禁止凭模式匹配或判型器直接定模型；必须先出读题审计报告（逐段拆解+约束+歧义+建模候选+图表计划），
   **未经用户确认不得进入求解**；用户确认记录写入 evidence-ledger。宁可慢、宁可多问，不抢跑。
   详见 `modules/kickoff-audit.md`。
3. **禁伪造**：数字、方法归属、实验结果不得编造；拿不准标"待确认"并给置信度。
4. **证据留痕**：每个关键结论可回溯到代码/数据/页码；语料引用标注 `年-赛道-paper_id-页码`。
5. **AI 使用（2026 规定）**：AI 仅作辅助，不替代独立思考与核心创新；AI 输出须理解后用、用自己的话写。
   使用 AI 辅助数据分析或编程、或将 AI 输出的模型/公式写入论文时，按对应规定标注工具名、版本/型号、开发者/机构和发布日期；无推导、无引用、无可确认来源的模型公式一律不写。未使用 AI 不得虚构披露。细则见 `modules/submission.md` 与 `docs/OFFICIAL_FORMAT_2026.md`。
6. **官方规则最高**：页数/格式/署名/提交方式以官方通知覆盖本仓库任何默认；当前 2026 格式基线见 `docs/OFFICIAL_FORMAT_2026.md`。
7. **不承诺获奖**：本 skill 提升工程与表达质量，不承诺任何奖项结果。
8. **语料只读**：Desktop 获奖论文语料根只读，不删除/移动/重命名任何用户文件。
9. **赛道字母按届重置**：A–F 只是当年题号，不跨届固定含义。
10. **2026 封皮硬规则**：正式提交 PDF 的物理首页必须是逻辑第 0 页参赛信息封皮，四个 logo 不替换，封皮不显示页码；
    第二页起为页码 1 的摘要与匿名正文。学校、姓名和队伍编号只允许出现在封皮；纯匿名稿只能用于内部审阅，不能作为 2026 正式上传稿。
11. **证据型策略门**：内置 grill-me 式“每次只问一个决策并给推荐”与 ponytail 式“最简充分”原则。每个小问的基线跑通后，如候选方案已有同口径实测且形成真实取舍，最多暂停一次，按 `solving.md` 给出一个 A/B/C 选择、推荐答案、数据与图；用户选择写入 evidence-ledger 后再切换主路线。未实测不得称“优化”，收益不确定或复杂度代价不成比例时推荐保留基线。
12. **参考模板隔离**：用户提供的第二十三届 LaTeX 包是社区内容参考，不是官方模板。写作阶段可按 `docs/TEMPLATE_CONTENT_MAPPING_23RD.md` 吸收任务映射、数据审计、证据链、不确定性与复现元数据；生产 LaTeX 禁止引用其类文件、目录、组合 logo 或带“第二十二届”的过期标题资产。任何冲突均由 `docs/OFFICIAL_FORMAT_2026.md` 与官方 Word 文件裁决。
13. **Figure 总数先提案、后锁定**：读完题面与数据后，先按全局与各小问逐张列出 Figure、证据来源、面板和必要性，再向用户报建议总数；用户可回复“锁定 N 张”或“图片总数：XX”。未明确确认不得批量生成正式论文图。锁定值按论文中带图号的顶层 `figure/figure*` 环境计数：复合图的子面板不另计，封皮 logo 与表格不计；最终 visual plan 与 LaTeX 必须精确一致。用户要求增加时，先为新增 Figure 补独立分析或实验；证据不足就报告缺口与可支撑上限，严禁伪造或换图型凑数。详见 `figures-interface.md`。
14. **篇幅由用户裁决，写作最简充分**：Figure 总数锁定后，报告由真实证据支撑的预计完整 PDF 页数区间，请用户回复“论文总页数：XX”或“论文长度：证据充分即可”；这不是官方门槛。增加 Figure 可以带来相应的方法、结果、解释和验证篇幅，但不能靠套话、重复图表、无效复杂度、放大字号/图表、强制分页或无关附录增页。代码、LaTeX 与自动化修改使用 ponytail 的 YAGNI/最简充分原则；论文文字按 `deai-writing.md` 做证据化去 AI 味，不能把 coding skill 当作文字润色器。

## 4. 本地脚本索引

| 脚本 | 用途 |
|---|---|
| `scripts/contest_init.py` | 比赛日初始化工作目录骨架 |
| `scripts/corpus_build.py` / `corpus_cards.py` | 语料抽文与卡片（已跑通 729 篇） |
| `scripts/build_latex.py` / `audit_tex.py` / `audit_paper.py` | LaTeX 论文构建与审计 |
| `scripts/build_docx.py` / `audit_docx.py` | Word 论文构建与审计 |
| `scripts/visual_plan_init.py` / `visual_plan_audit.py` | 论文视觉计划 |
| `scripts/playbook_match.py` | 题面→原型/方法卡规则匹配 |
| `scripts/evidence.py` | 证据账本合规校验 |
| `scripts/progress.py` | P0–P6 内容级门禁（`--gate Pn` / `--all`） |
| `scripts/review.py` | 评审团启发式打分（非真评审） |
| `scripts/submission_audit.py` | 提交前审计（页数/匿名/AI披露/附件） |
| `scripts/paper_checklist.py` | 优秀论文自检表机检（138 条；`--tex/--problems/--archetype`、`--mark` 人工裁决、`--strict`、sidecar JSON） |
| `scripts/doctor.py` | 一键环境自检（Python/依赖/TeX/字体/MATLAB/Word） |
| `scripts/render_roadmap.py` | 技术路线图渲染（YAML→PNG/PDF/MMD/DOT） |
| `scripts/audit_roadmap.py` | 技术路线图规格审计（schema+图结构+安全色） |

## 5. 评分与自评

- 官方四标准：假设合理性、建模创造性、结果正确性、文字表述清晰度。
- 自评量表与锚点见 `docs/SCORING_RUBRIC.md`（经验推断，非官方细则）。
- 知识库蒸馏方法与留出盲检结果见 `docs/DISTILLATION_METHOD.md`。
- 论文图种选型与八原型必备图清单见 `docs/FIGURE_COOKBOOK.md`。
- 环境/编译/字体常见坑与修复见 `docs/TROUBLESHOOTING.md`。
- 一键开箱玩具样例见 `docs/examples/quickstart/`（题面→匹配→路线图→xelatex 全链路）。

## 6. 完成报告纪律

每轮任务结束，按三态回报：**implemented**（已实现）、**tested**（已跑通验证）、
**live-validated pending**（待比赛日/真机验证）。不把"写完脚本"说成"跑通脚本"。

最终 LaTeX/PDF 只有在三轮检查完成后才可标记 `tested`：① 源码/自动化审计；
② XeLaTeX 编译并逐页视觉检查；③ 从干净交付包重新编译、复审匿名性与页码。
