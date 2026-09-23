# modules/technical-roadmap.md · 技术路线图体系（论文图1）

> **目标**：把"数据→预处理→各小问模型链→求解→验证→结论"这条主链路画成一张**评审一眼看懂**的技术路线图，作为论文**图1**（结构图/流程图之首）。配套一套 YAML 规格 + 渲染器 + 校验器，保证图与正文、与读题审计约束**同源一致**，杜绝"图上一套、正文一套"的评审扣分项。
>
> 上游：读题审计（`kickoff-audit.md` §3.6 图表计划）在题目含相互关联的多问、跨问数据链或训练/验证/测试边界时把论文级总流程图列为必需的图1；方法链取自 `playbooks/<原型>/` 方法卡；配色对接 `skills/academic-figure`（色盲友好语义色板）。
> 下游：渲染器 `scripts/render_roadmap.py`、校验器 `scripts/audit_roadmap.py`、规格 `assets/roadmap/roadmap.schema.json`、原型模板 `assets/roadmap/templates/`。

## 1. 为什么图1通常应是论文级总流程图

在已蒸馏语料的图序中，**结构图/流程图较常见**（全语料流程图/框图 158、结构图 153，见 `figures-interface.md` §6）。当技术路线图确有助于理解时，第一张方法图应回答三个问题；若题目流程简单，不为凑图强行添加：

1. **你拿到数据后干了什么**（输入→预处理）；
2. **每个小问用了什么模型、为什么**（模型链，回链读题约束）；
3. **你怎么知道结果可信**（验证、选择与独立测试边界）。

技术路线图就是这张"总览地图"。它不是装饰，是**建模思路的可视化承诺**——正文每讲一个核心模型或验证边界，图上都能找到对应视觉锚点。

### 1.1 最终总图与结构草图不是同一种产物

复杂、多问、数据密集论文的最终 F01 必须是**论文专属完整框架图**，而不是把六层名称排成几只等权文本框。正式总图调用 `paper-framework-figure-studio-pro` 的完整论文框架路线，并以本项目题面、reading audit、evidence ledger、视觉计划、模型/求解脚本、结构化结果和论文源稿为唯一语义来源。其最低可见内容为：

1. 真实输入或数据对象，以及必要的质量控制与拆分；
2. 每个小问的核心机制和真实输入/输出，不把变量或指标误画成同级大模块；
3. 小问之间真实存在的数据流、模型状态或结果传递；
4. 训练/校准/验证/测试的方向与隔离，反馈箭头只回到确实参与选择的模块；
5. 与结论对应的评价、归因、不确定性或交付输出；
6. 能降低理解成本的真实数据/结果缩略图、内部机制小图或必要公式，而非装饰图标。

`roadmap.yaml + render_roadmap.py` 仍保留，但定位改为：语义清单、早期结构草图、低复杂度题的最简充分图，或无图像生成条件时的可恢复后备。对于同时含多问、真实场图/时空图、受控消融或验证闭环的论文，简单框图不能直接冒充最终 F01；必须先经过完整框架图设计与人工选择门禁。无论采用哪条路线，图中关系都必须由证据支持。

### 1.2 论文级总图的客观质量门槛

- **完整而不扁平**：宏观分区、核心模块、内部机制、变量/指标四级层次明确；变量、阈值和指标默认作为边标签、端口或附着标记，不升格为大框。
- **一眼可读**：主阅读路径明确；实线、虚线、颜色和面板含义在图内短图例或图注中闭合；同向多条线能合并就合并。
- **内容可核验**：每个模块、箭头、缩略图、数字和结论都能回链到题面、脚本或结果文件；不得用视觉生成补写不存在的深度模型、连接或性能收益。
- **版面可用**：按约 165 mm 版心设计；正式位图以实际插入宽度下 300 dpi 为目标，优先保留生成的最高分辨率原图。若用户明确选定的正式候选不足 300 dpi，不得用低清截图替代或用伪放大冒充新增细节；应记录例外，并以最终打印尺度逐字检查文字、箭头和小图确实清楚、无遮挡、无挤压。
- **图文共生**：图片承载视觉路径，图注说明颜色/箭头/阶段语义，正文说明为什么看这张图以及它支持什么结论；图注不能替代图中不可省略的核心步骤。

### 1.3 中文 F01 的可见文本合同

中文论文不能把英文候选原样塞进正文，也不能在最后一步凭感觉逐词覆盖。调用 `paper-framework-figure-studio-pro` 时，S1 与 S4 的现有 `visible_text_contract` 必须同时写入以下项目；这是对原合同的项目级补充，不另造阶段：

1. **中文优先**：自然语言节点、边说明、图例和警示语默认使用简体中文。英文论文使用源语言，不强行中文化；普通结果图继续按通用图表规则执行。
2. **技术 token 注册**：变量、数学符号、单位、数据集 ID、算法专名和公认缩写逐项登记精确写法、来源锚点与是否必须可见。例如 $Z_H$ 不能被改成 `ZH` 后再任意翻译，`IsotonicRegression` 应按真实含义写“保序回归”，不能望文写成“等距回归”。
3. **逐标签账本**：对每个可见标签记录“源标签、中文显示、允许断行、保留英文/符号理由、证据锚点”。中文变长时先缩短同义表达、做最多两行的语义断行或扩框；不得拆开变量、数字与单位，也不得为塞字删除限定词。
4. **最终尺度文字**：可编辑矢量文字按实际 LaTeX 插入宽度计算有效字号，宏观分区至少 11 pt、模块节点至少 10 pt，边/端口、内部微标签和图例至少 9 pt。生成式 PNG 没有可验证的字号元数据，不得把像素高度冒充 pt；栅格兜底改按原生像素和实际插入宽度计算物理墨迹高度，宏观分区至少 3.0 mm、模块节点至少 2.5 mm、边/端口与内部微标签至少 2.0 mm、图例至少 2.2 mm，并保存量测证据。达不到时必须重排；放大低清图或只看聊天预览不算通过。
5. **零碰撞**：文字—文字、文字—连接线、文字—边界溢出、裁切、乱码各为 0；内边距至少约半个中文字宽，箭头端点和方向不得被中文标签覆盖。
6. **语义先于翻译**：翻译前再次对照求解代码和正文公式。若原候选已经把并联误画成串联、把变量写错或把指标放入错误模块，先修语义，再做中文化，不能“忠实翻译错误图”。

推荐把下列内容写进 S1/S4 提示包；S4 可以调整具体标签，但不能降低字号阈值或放松碰撞门禁：

```yaml
visible_text_contract:
  language_policy: zh_primary_preserve_exact_tokens
  label_ledger: <源标签 -> 中文标签 -> 断行 -> 证据锚点>
  technical_token_registry: <精确缩写/符号/单位/专名及来源>
  target_insert_width_mm: <实际插入宽度>
  vector_minimum_effective_pt: {macro_group: 11, node: 10, edge_or_port: 9, internal_micro: 9, legend: 9}
  raster_minimum_ink_mm: {macro_group: 3.0, node: 2.5, edge_or_port: 2.0, internal_micro: 2.0, legend: 2.2}
  allowed_violations: {text_text_collision: 0, text_connector_collision: 0, boundary_overflow: 0, clipping: 0, garbled_cjk: 0}
```

`paper-framework-figure-studio-pro` 的公开流程仍止于 S5。若用户在 S5 后明确要求把已经选定的候选改成中文，华为杯流程可做一次**独立 consumer-side 本地化适配**：必须保留未改的 S5 源图，在独立目录记录用户授权、源/目标哈希、完整提示词、标签账本与视觉 QA；不得把它命名为 S6，也不得静默覆盖 stage-local 候选。最终以 `scripts/audit_framework_figure.py` 校验记录，再进入本模块 §7 的入稿门禁。

## 2. YAML 结构草图分支的要素规范（六层主链路 + 可选控制边）

本节只约束 `roadmap.yaml + render_roadmap.py` 的语义草图、低复杂度充分图或恢复后备，不约束 `paper-framework-figure-studio-pro` 生成的复杂论文正式 F01。YAML 路线图按下列六层组织，每层是一个 `layer`；不得把六层等权空框直接复制为复杂论文正式总图：

| 层序 | layer id | 含义 | 节点必须标注 |
|---|---|---|---|
| 1 | `input` | 数据输入层：原始数据、附件、外部数据 | 数据来源/表名 |
| 2 | `preprocess` | 预处理：清洗、缺失/异常、特征工程、标准化 | 方法名 |
| 3 | `model` | 各小问模型链：每个小问至少一个节点 | **方法名 + 对应章节号** |
| 4 | `solve` | 求解：求解器/算法/数值方法 | 求解工具（Gurobi/ode45/SVM…） |
| 5 | `validate` | 验证：独立验证、灵敏度、鲁棒性、统计检验 | 验证手段 |
| 6 | `output` | 结论输出：各小问答案、方案、推广 | 交付物 |

**反馈/控制边（按证据决定）**：只有验证、调参、校准或模型选择确实把信息反馈给上游模块时，才从对应验证节点画**虚线控制箭头**，并标清“调参”“校准”或“选择”等真实语义。独立测试、最终评价和只读审计不得画返回箭头；解析求解或无需调参的题可以完全没有反馈边。YAML 中用 `metadata.feedback_expected` 显式声明是否应有反馈，虚线使用 `edges[].type = dashed`。缺少真实反馈不是缺点，虚构反馈才是错误。

## 3. 小问映射与约束回链（图与读题审计同源）

- **每个小问必须映射到至少一个模型节点**。在 `subquestion_mapping` 里登记：小问编号（如 `Q1`/`Q2`/`Q3`）→ 节点 id 列表。校验器会逐小问检查"是否有节点"，缺哪个小问就报哪个。
- **每个模型节点回链读题审计的约束编号**：节点字段 `constraint_ref` 填 `C1`/`C2`…（来自 `kickoff-audit.md` §2 抽出的约束）。这样图上每个建模选择都有题面证据，呼应"无证据的建模选择一律标待论证"。
- **节点回链正文章节号**：节点字段 `chapter_ref` 填如 `§4.2`。正文写到该模型时，图上节点的章节号必须对得上——这是"图与正文不一致"扣分项的防线。
- 节点字段 `method` 填方法名（如"NSGA-II 多目标优化"），**不允许空**；空方法名的节点是裸框，校验器报错。

## 4. 变更同步（图随模型走）

模型/方法/数据一旦变更，按 `change-management.md` 的变更影响评估走，**必须同步改正式图及其语义来源**：

1. 先更新 reading audit、evidence ledger、视觉计划、正文与真实结果文件，确保唯一事实来源一致；
2. 若正式图属于复杂论文分支，更新 figure-studio 的 brief/state/manifest，重走受影响阶段，重新选择正式候选并更新校验和；再把**该候选**同步到 LaTeX，重跑六联门禁。任何 YAML 渲染脚本都不得覆盖这张正式 F01；
3. 若正式图确属 YAML 低复杂度分支，再修改 spec 中的 `method`/`chapter_ref`/`constraint_ref`，运行 `render_roadmap.py` 和 `audit_roadmap.py`；
4. 在 `change-management.md` 的变更记录里注明使用哪条分支、正式源图路径/校验和及“技术路线图已同步”。

> **红线：图与正文章节号对不上 = 评审扣分项。** 换了模型却忘了改图，比没画路线图更糟——评委照着图找正文找不到对应章节，直接怀疑严谨性。

## 5. 配色与排版

- **色盲友好配色**：直接复用 `skills/academic-figure` 的语义色板（见 `references/color-palettes.md`），**禁止** jet/rainbow/hsv/tab10/Set1 等默认色板。各层配色按语义分配（蓝=输入/基准、绿=模型/治疗、橙=求解、紫=验证、红=强调/结论小面积、灰=背景），详见渲染器 `LAYER_COLORS`。
- **冗余编码**：颜色**不单独承担区分**——每个节点同时有文字标签、层级位置、（可选）形状，满足色盲/黑白打印可区分。
- **分层布局**：每层一列（或一排），层内节点纵向堆叠；若存在真实反馈/控制边，其虚线单独走线，不与主链路实线重叠。
- **字号规范**：节点标题 ≥ 10pt（缩放后仍可读），层标签 ≥ 11pt，反馈箭头标注 ≥ 9pt。YAML 分支导出 PDF 矢量和 ≤500KB 的 PNG 预览；复杂论文正式 F01 不设 500KB 人为上限，以有效分辨率、文本可读性和无压缩伪影为准。
- **中文字体**：优先 Microsoft YaHei，回退链 SimHei → Noto Sans CJK → Source Han；系统无任何 CJK 字体时，节点自动切换 `label_en` 英文标签优雅回退，**不崩溃、不出方块**。

## 6. 四种产物（同时导出）

渲染器对一份 YAML spec 同时导出四种格式，保证"论文用矢量、协作可编辑、评审可预览"：

| 格式 | 用途 |
|---|---|
| `.pdf` | 论文正文插入（矢量，缩放不糊） |
| `.png` | 预览/PPT/在线评审（≤500KB） |
| `.mmd` | Mermaid flowchart 源码，可在 Markdown/在线编辑器继续改 |
| `.dot` | Graphviz 源码，可 `dot -Tpdf` 重排 |

上述四种产物只针对 YAML 路线图分支。采用 `paper-framework-figure-studio-pro` 时，必须保留其 stage-local 正式候选原图、注册来源、提示/审计记录与校验和；论文只复制**用户选定或按既定授权选定的最高分辨率正式图**，不得拿聊天截图、缩略图或低分辨率预览替代。

## 7. 入稿六联门禁（生成完成仍不算结束）

正式 F01 必须逐项满足，缺一项即不得标记 `qa_pass`：

1. `selected_source_exists`：正式候选源图存在，校验和已记录；
2. `latex_bound`：源稿中的 `\includegraphics` 或受控宏明确引用该文件，不得只留在输出目录；
3. `body_reference_before_figure`：图前正文使用唯一 `\ref{fig:...}` 说明读者为何看图；
4. `caption_complete`：图注说明图的范围、主路径、实/虚线或颜色等必要语义；
5. `post_figure_interpretation`：图后正文指出至少一个可核验关系、数字或边界，并承接下节；
6. `compiled_pdf_visible`：从干净交付包双遍编译后，在最终 PDF 中定位图号并逐页肉眼检查，确认文字不挤、箭头不遮、缩略图可辨、没有裁切。

中文复杂 F01 还必须附带哈希绑定的 `framework_text_qa`：文档语言、本地化来源（S1/S4 原生或用户明确授权的 S5 后 consumer 适配）、原 S5 与本地化图的双重来源、提示词/适配记录、标签账本、保留 token、实际插入宽度、矢量有效字号或栅格物理墨迹量测，以及碰撞/溢出/裁切/乱码/语义错配计数。任何计数非 0 或文字低于 §1.3 对应下限，均不得 `qa_pass`。论文阶段还须解析 `main.tex` 的真实 `\includegraphics` 或受控包装宏并精确定位目标文件，再核验哈希绑定的编译 PDF：位图比较实际显示对象的解码像素哈希，不能只比尺寸；矢量图记录 `compiled_pdf_figure_bbox_pt=[x0,y0,x1,y1]`，并将该页区域与源图渲染结果比对。不能只写 `compiled_pdf_visible: true`。

推荐在视觉计划或 checkpoint 中记录：

```yaml
framework_figure_binding:
  figure_id: F01
  selected_source: <highest-resolution formal candidate>
  selected_source_sha256: <sha256>
  latex_target: <paper figure path>
  label: fig:route
  body_reference_before_figure: true
  caption_complete: true
  post_figure_interpretation: true
  compiled_pdf: <compiled PDF path>
  compiled_pdf_sha256: <sha256>
  compiled_pdf_page: <physical page>
  compiled_pdf_figure_bbox_pt: <[x0,y0,x1,y1]; vector_text only>
  compiled_pdf_visible: true
```

权威视觉计划也要在同一个 F01 条目中登记消费路径；不要只在 checkpoint 里另写一份。可用初始化器生成 schema 合法的草案，再补真实证据字段：

```powershell
python scripts/visual_plan_init.py --output 求解/视觉计划.json --project-title "论文题目" --problem-id 问题一 --complex-f01
```

该条目固定使用 `role=complex_multi_question_framework` 和 `paper-framework-figure-studio-pro` 路线，并以项目内相对 JSON 路径登记 `framework_binding` 与同目录 `framework_audit_report`。整份计划只能出现一个 `figure_id=F01`；初始化值只是待补草案，不能代替真实图、binding 或审计报告。

## 8. YAML 草图/低复杂度分支快速上手

```powershell
# 1. 从对应原型模板复制一份，按题目改节点
copy assets/roadmap/templates/optimization.yaml my_roadmap.yaml

# 2. 渲染（默认全部格式）
python scripts/render_roadmap.py --spec my_roadmap.yaml --outdir 求解/路线图

# 3. 校验（覆盖度/孤立节点/配色）
python scripts/audit_roadmap.py --spec my_roadmap.yaml
```

8 个原型的预填模板见 `assets/roadmap/templates/`：optimization / evaluation / prediction / classification-cv / mechanism / signal / spatial-graph / simulation。每个模板的注释说明了如何改节点、如何补小问映射；这些模板不能直接作为复杂多问题的正式 F01。

## 9. 常见错误（评审扣分点，逐条对照）

- **节点无方法名**：框里只有"模型1""模型2"，没有 NSGA-II / SVM / ODE 这种真名 → 校验器 `node_method_empty` 报错。
- **小问遗漏**：Q3 在图上找不到任何节点 → `subquestion_uncovered` 报错并点名哪个小问。
- **反馈关系失真**：声明 `feedback_expected=true` 却无虚线控制边，或独立测试/最终评价反向连接训练模块 → 退回证据审计；若流程本来无反馈，应声明 `false` 并保持无回边。
- **配色不色盲友好**：用了红蓝/红绿之外的不可区分对、或用了禁用色板 → `color_not_cbf_safe` 报错。
- **图与正文章节号对不上**：节点 `chapter_ref` 是 §4.2，正文该模型其实在 §4.3 → 人工终稿核对（见 `change-management.md`）。
- **孤立节点**：某个节点既无入边也无出边（输入层/输出层除外）→ `isolated_node` 报错并点名哪个节点。
- **中文方块字**：未设中文字体硬渲 → 用 `label_en` 回退或装 CJK 字体。
- **只生成未入稿**：正式图停留在 figure-studio 输出目录，论文仍引用旧的简单框图 → 六联门禁失败，必须替换源稿并重新编译。
- **拿低清截图替代正式源图**：聊天截图看起来正确，却在版心宽度下不足 300 dpi → 回到 stage-local 正式原图；不得放大截图。
- **总图只有模块名**：每问只有一个标题框，没有内部机制、真实数据/结果锚点或验证边界 → 退回完整框架设计，不以图注补救空框。

## 10. 边界

- 本模块只规定"路线图怎么画、怎么校验、怎么同步"，不替代 `figures-interface.md` 的通用出图规范；满足复杂多问判定条件时论文级总流程图是图1，其余结果图走 visual plan。简单题若总图不能增加理解，不强行添加。
- 样例数据一律虚构/脱敏（见 `docs/examples/roadmap/`），不碰 Desktop 真实语料。
- 模型选型本身仍由 `kickoff-audit.md` 读题审计 + 用户 P1 确认决定；路线图只把已确认的模型链画出来，不替你选模型。
