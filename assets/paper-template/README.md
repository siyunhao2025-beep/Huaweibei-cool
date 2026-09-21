# 2026 华为杯正式提交论文模板

本目录的默认入口是 example.tex。它依据用户提供的第二十三届官方 Word 文件校正，详细依据见 docs/OFFICIAL_FORMAT_2026.md。

## 官方版式已落实

- A4；页边距：上 30 mm、下 17.5 mm、左/右 22.5 mm。
- 物理第 1 页为官方参赛信息封皮，页码 0；物理第 2 页同时包含题目、摘要和关键词，论文页码从 1 开始。
- 完整摘要后的下一页直接开始正文，**不生成目录**。
- 无页眉；学校、队号和队员姓名只出现在封皮，封皮后的摘要与正文匿名。
- 题目三号黑体，一级标题四号黑体居中，其他汉字小四宋体，单倍行距。
- 前置标签“题目/摘要/关键词”按官方 Word 模板使用隶书 18 pt。
- 官方 Word 模板的 ASCII/HAnsi 样式使用 Times New Roman；模板将排版文本中的英文、阿拉伯数字和西文标点统一为 Times New Roman。Overleaf 没有该微软字体时自动回退为 TeX Gyre Termes；公式使用 TeX Gyre Termes Math，代码保留等宽字体。
- 摘要使用 `\textbf{...}` 选择性突出主要模型、决定性数值（连同单位）和核心结论/创新点；普通数字不机械加粗，禁止整句或整段加粗。

## 页数结论（核对至 2026-09-21）

- 当届官方材料只明确摘要篇幅**一般不超过两页**；没有给出正文最低页数、正文上限或全文总页数上限。
- 不以 45 页、历史获奖论文平均页数或固定字数作为目标。优先保证每问“任务—模型—求解—结果—验证—结论”闭环，再删重复背景、教科书式算法介绍、机械图表复述和无关推导。
- 若赛题 PDF、竞赛系统或后续官方通知另行给出明确限制，以更新且更具体的要求为准，并在最终 PDF 上执行上限审计。
- 正常章节收尾留白可以保留；应修复多余分页、浮动体失控或排版错误造成的异常大面积空白，不得缩小官方字号、行距或页边距来挤页。

## 两个入口

- `example.tex`：2026 正式提交默认入口，包含第 0 页封皮，随后从匿名摘要第 1 页开始。
- `example-with-identity-cover.tex`：保留的显式命名兼容入口，版式与 `example.tex` 相同。

实名封面的虚线竖框和页面四角标记是 Word 编辑界面的表格网格线/裁切标记，不属于打印版式，因此 LaTeX PDF 不输出这些辅助线。四个徽标资源来自用户提供的第二十三届官方 Word 模板。

## Overleaf 使用

1. 上传 `example.tex`、`gmcmthesis.cls`、`gmcm-title.sty`、`gmcm.bst` 和四个 `figures/identity-*` 徽标文件；将 `example.tex` 重命名为 `main.tex`（或设为主文件）。
2. 在 Menu → Compiler 选择 XeLaTeX。
3. 填写 `\schoolname`、`\baominghao`、`\membera`、`\memberb`、`\memberc`；再替换题目、摘要、关键词和正文，不添加目录。
4. 编译两遍，确认物理第 1 页为页码 0 的封皮、物理第 2 页摘要为页码 1，且封皮之外没有身份信息。

本仓库生成的 Overleaf ZIP 已放置可直接编译的 `main.tex`，并附 `章节模板/` 与 `华为杯_论文章节规范.md` 供写作时按需取用；这些辅助文件不会被 `main.tex` 自动载入。

竞赛系统只接收编译后的单个 PDF，不接收 Overleaf ZIP、TeX 源文件或单独的封皮图片。最终 PDF 按“题号字母+队伍编号”命名，并在提交 MD5 后保持文件不变。

标题字体优先使用 Windows 的华文新魏；Overleaf 缺少该字体时，gmcm-title.sty 会自动采用 TeX Live 自带的中文回退字体，仅影响三行赛事标题，不会替换正文宋体。西文字体的合法回退规则见上文；不要把 Times New Roman 字体文件打包上传或提交到仓库。

## 第二十三届社区 LaTeX 参考包

用户提供的 `第23届华为杯LaTeX模板.pdf` 及其源文件已在本机 skill 的 `reference-23rd-latex/` 装载并登记 SHA-256。该包的类文件头注明来源为 `latexstudio.net`，因此它是社区参考包，不是官方组织方发布的 LaTeX 模板。源包未附明确再分发许可，公开 GitHub 只保留 `source-manifest.json`、逐页映射和融合结果，不复制原件。

- 已吸收：摘要任务—方法—结果—验证—价值闭环、问题任务卡、数据审计、变量字典、Baseline—主模型证据链、结果解释、不确定性、模型评价、结论与复现元数据。
- 已拒绝：两页目录、该包的封面和类文件、组合 logo，以及写有“第二十二届”的过期 `title.pdf`。
- 生产模板不会引用参考目录；官方 Word/通知与 `docs/OFFICIAL_FORMAT_2026.md` 始终优先。
- 完整逐页映射与取舍理由见 `docs/TEMPLATE_CONTENT_MAPPING_23RD.md`，可直接使用的章节骨架见 `章节模板/`。

## 生成器与审计

\`audit_tex.py\` 的 \`--manifest\` 应传入原始 TeX-only 清单（例如 \`论文输入.json\`），而不是生成后的 \`main.inputs.json\`；后者仅用于追溯本次生成时实际写入的输入文件。

scripts/build_latex.py 从 TeX-only manifest 生成带正式封皮结构的主文件；scripts/audit_tex.py 检查输入顺序、无目录、封皮后匿名、页式和格式覆盖；scripts/build_docx.py 与 scripts/audit_docx.py 提供可选 Word 派生链。最终版式仍须以 PDF 视觉检查为准。

交付前固定做三轮：源码/测试审计 → XeLaTeX 编译并逐页看图 → 解压最终 Overleaf 包后重新编译与复审。三轮都通过才算模板验收完成。
