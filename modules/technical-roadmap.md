# modules/technical-roadmap.md · 技术路线图体系（论文图1）

> **目标**：把"数据→预处理→各小问模型链→求解→验证→结论"这条主链路画成一张**评审一眼看懂**的技术路线图，作为论文**图1**（结构图/流程图之首）。配套一套 YAML 规格 + 渲染器 + 校验器，保证图与正文、与读题审计约束**同源一致**，杜绝"图上一套、正文一套"的评审扣分项。
>
> 上游：读题审计（`kickoff-audit.md` §3.6 图表计划）把图1列为默认首图；方法链取自 `playbooks/<原型>/` 方法卡；配色对接 `skills/academic-figure`（色盲友好语义色板）。
> 下游：渲染器 `scripts/render_roadmap.py`、校验器 `scripts/audit_roadmap.py`、规格 `assets/roadmap/roadmap.schema.json`、原型模板 `assets/roadmap/templates/`。

## 1. 为什么图1必须是技术路线图

在已蒸馏语料的图序中，**结构图/流程图较常见**（全语料流程图/框图 158、结构图 153，见 `figures-interface.md` §6）。当技术路线图确有助于理解时，第一张方法图应回答三个问题；若题目流程简单，不为凑图强行添加：

1. **你拿到数据后干了什么**（输入→预处理）；
2. **每个小问用了什么模型、为什么**（模型链，回链读题约束）；
3. **你怎么知道结果可信**（验证→反馈迭代回路）。

技术路线图就是这张"总览地图"。它不是装饰，是**建模思路的可视化承诺**——正文每讲一个模型，图上都能找到对应节点。

## 2. 要素规范（六层主链路 + 反馈回路）

路线图必须自上而下（或自左而右）按下列六层组织，每层是一个 `layer`：

| 层序 | layer id | 含义 | 节点必须标注 |
|---|---|---|---|
| 1 | `input` | 数据输入层：原始数据、附件、外部数据 | 数据来源/表名 |
| 2 | `preprocess` | 预处理：清洗、缺失/异常、特征工程、标准化 | 方法名 |
| 3 | `model` | 各小问模型链：每个小问至少一个节点 | **方法名 + 对应章节号** |
| 4 | `solve` | 求解：求解器/算法/数值方法 | 求解工具（Gurobi/ode45/SVM…） |
| 5 | `validate` | 验证：独立验证、灵敏度、鲁棒性、统计检验 | 验证手段 |
| 6 | `output` | 结论输出：各小问答案、方案、推广 | 交付物 |

**反馈迭代回路（强制）**：从 `validate` 层（或 `solve` 层）画一条**虚线箭头**回到 `model` 层，箭头上标注"**迭代/调参/换模型**"。没有这条回路，路线图就是"一锤子买卖"，评审会扣"缺迭代优化"分。虚线用 `edges[].type = dashed`。

## 3. 小问映射与约束回链（图与读题审计同源）

- **每个小问必须映射到至少一个模型节点**。在 `subquestion_mapping` 里登记：小问编号（如 `Q1`/`Q2`/`Q3`）→ 节点 id 列表。校验器会逐小问检查"是否有节点"，缺哪个小问就报哪个。
- **每个模型节点回链读题审计的约束编号**：节点字段 `constraint_ref` 填 `C1`/`C2`…（来自 `kickoff-audit.md` §2 抽出的约束）。这样图上每个建模选择都有题面证据，呼应"无证据的建模选择一律标待论证"。
- **节点回链正文章节号**：节点字段 `chapter_ref` 填如 `§4.2`。正文写到该模型时，图上节点的章节号必须对得上——这是"图与正文不一致"扣分项的防线。
- 节点字段 `method` 填方法名（如"NSGA-II 多目标优化"），**不允许空**；空方法名的节点是裸框，校验器报错。

## 4. 变更同步（图随模型走）

模型/方法/数据一旦变更，按 `change-management.md` 的变更影响评估走，**必须同步改路线图**：

1. 改 YAML spec 里对应节点的 `method`/`chapter_ref`/`constraint_ref`；
2. 重新跑 `scripts/render_roadmap.py --spec <yaml>` 出 PNG+PDF；
3. 重新跑 `scripts/audit_roadmap.py --spec <yaml>` 确认覆盖度/孤立节点仍 PASS；
4. 在 `change-management.md` 的变更记录里加一行"技术路线图已同步"。

> **红线：图与正文章节号对不上 = 评审扣分项。** 换了模型却忘了改图，比没画路线图更糟——评委照着图找正文找不到对应章节，直接怀疑严谨性。

## 5. 配色与排版

- **色盲友好配色**：直接复用 `skills/academic-figure` 的语义色板（见 `references/color-palettes.md`），**禁止** jet/rainbow/hsv/tab10/Set1 等默认色板。各层配色按语义分配（蓝=输入/基准、绿=模型/治疗、橙=求解、紫=验证、红=强调/结论小面积、灰=背景），详见渲染器 `LAYER_COLORS`。
- **冗余编码**：颜色**不单独承担区分**——每个节点同时有文字标签、层级位置、（可选）形状，满足色盲/黑白打印可区分。
- **分层布局**：每层一列（或一排），层内节点纵向堆叠；反馈回路虚线单独走线，不与主链路实线重叠。
- **字号规范**：节点标题 ≥ 10pt（缩放后仍可读），层标签 ≥ 11pt，反馈箭头标注 ≥ 9pt；导出 PDF 矢量、PNG ≤ 500KB 预览。
- **中文字体**：优先 Microsoft YaHei，回退链 SimHei → Noto Sans CJK → Source Han；系统无任何 CJK 字体时，节点自动切换 `label_en` 英文标签优雅回退，**不崩溃、不出方块**。

## 6. 四种产物（同时导出）

渲染器对一份 YAML spec 同时导出四种格式，保证"论文用矢量、协作可编辑、评审可预览"：

| 格式 | 用途 |
|---|---|
| `.pdf` | 论文正文插入（矢量，缩放不糊） |
| `.png` | 预览/PPT/在线评审（≤500KB） |
| `.mmd` | Mermaid flowchart 源码，可在 Markdown/在线编辑器继续改 |
| `.dot` | Graphviz 源码，可 `dot -Tpdf` 重排 |

## 7. 快速上手

```powershell
# 1. 从对应原型模板复制一份，按题目改节点
copy assets/roadmap/templates/optimization.yaml my_roadmap.yaml

# 2. 渲染（默认全部格式）
python scripts/render_roadmap.py --spec my_roadmap.yaml --outdir 求解/路线图

# 3. 校验（覆盖度/孤立节点/配色）
python scripts/audit_roadmap.py --spec my_roadmap.yaml
```

8 个原型的预填模板见 `assets/roadmap/templates/`：optimization / evaluation / prediction / classification-cv / mechanism / signal / spatial-graph / simulation。每个模板的注释说明了如何改节点、如何补小问映射。

## 8. 常见错误（评审扣分点，逐条对照）

- **节点无方法名**：框里只有"模型1""模型2"，没有 NSGA-II / SVM / ODE 这种真名 → 校验器 `node_method_empty` 报错。
- **小问遗漏**：Q3 在图上找不到任何节点 → `subquestion_uncovered` 报错并点名哪个小问。
- **无反馈回路**：整张图全是实线、没有"迭代/调参/换模型"虚线 → `no_feedback_loop` 警告。
- **配色不色盲友好**：用了红蓝/红绿之外的不可区分对、或用了禁用色板 → `color_not_cbf_safe` 报错。
- **图与正文章节号对不上**：节点 `chapter_ref` 是 §4.2，正文该模型其实在 §4.3 → 人工终稿核对（见 `change-management.md`）。
- **孤立节点**：某个节点既无入边也无出边（输入层/输出层除外）→ `isolated_node` 报错并点名哪个节点。
- **中文方块字**：未设中文字体硬渲 → 用 `label_en` 回退或装 CJK 字体。

## 9. 边界

- 本模块只规定"路线图怎么画、怎么校验、怎么同步"，不替代 `figures-interface.md` 的通用出图规范；路线图是图1，其余结果图走 visual plan。
- 样例数据一律虚构/脱敏（见 `docs/examples/roadmap/`），不碰 Desktop 真实语料。
- 模型选型本身仍由 `kickoff-audit.md` 读题审计 + 用户 P1 确认决定；路线图只把已确认的模型链画出来，不替你选模型。
