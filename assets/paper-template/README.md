# 2026 华为杯匿名论文模板

本目录的默认入口是 example.tex。它依据用户提供的第二十三届官方 Word 文件校正，详细依据见 docs/OFFICIAL_FORMAT_2026.md。

## 官方版式已落实

- A4；页边距：上 30 mm、下 17.5 mm、左/右 22.5 mm。
- 第 1 页同时包含题目、摘要和关键词；页脚中部显示阿拉伯页码 1。
- 完整摘要后的下一页直接开始正文，**不生成目录**。
- 无页眉；默认入口不生成学校、队号、成员、导师或 logo 封面。
- 题目三号黑体，一级标题四号黑体居中，其他汉字小四宋体，单倍行距。
- 前置标签“题目/摘要/关键词”按官方 Word 模板使用隶书 18 pt。

## 两个入口不要混用

- `example.tex`：正式匿名论文的默认入口，摘要页编号从 1 开始。
- `example-with-identity-cover.tex`：按官方 Word 和用户提供截图补齐的第 0 页参赛信息封面，随后仍从匿名摘要第 1 页开始。它会输出学校、队号和队员姓名，**仅当竞赛系统或组织方明确要求实名封面时使用**。

实名封面的虚线竖框和页面四角标记是 Word 编辑界面的表格网格线/裁切标记，不属于打印版式，因此 LaTeX PDF 不输出这些辅助线。四个徽标资源来自用户提供的第二十三届官方 Word 模板。

## Overleaf 使用

1. 匿名稿上传 `example.tex`、`gmcmthesis.cls` 和 `gmcm-title.sty`；将 `example.tex` 重命名为 `main.tex`（或在 Overleaf 设置为主文件）。
2. 在 Menu → Compiler 选择 XeLaTeX。
3. 只替换匿名题目、摘要、关键词和正文；不要添加任何身份字段，也不要添加目录命令。
4. 编译两遍，再人工确认第 1 页页码为 1、无页眉、摘要后的下一页是正文。

若系统明确要求实名封面，改用 `example-with-identity-cover.tex`，并连同 `figures/identity-cpipc.png`、`identity-gmcm.png`、`identity-huawei.jpg`、`identity-xjtu.png` 上传。填写 `\schoolname`、`\baominghao`、`\membera`、`\memberb`、`\memberc` 后调用 `\makeidentitycover`；不要把这个版本送入匿名提交审计。

标题字体优先使用 Windows 的华文新魏；Overleaf 缺少该字体时，gmcm-title.sty 会自动采用 TeX Live 自带的中文回退字体，仅影响三行赛事标题，不会替换正文宋体。

## 生成器与审计

\`audit_tex.py\` 的 \`--manifest\` 应传入原始 TeX-only 清单（例如 \`论文输入.json\`），而不是生成后的 \`main.inputs.json\`；后者仅用于追溯本次生成时实际写入的输入文件。

scripts/build_latex.py 从 TeX-only manifest 生成匿名主文件；scripts/audit_tex.py 检查输入顺序、无目录、匿名、页式和格式覆盖；scripts/build_docx.py 与 scripts/audit_docx.py 提供同一格式基线的可选 Word 派生链。最终版式仍须以 XeLaTeX 生成的 PDF 视觉检查为准。

交付前固定做三轮：源码/测试审计 → XeLaTeX 编译并逐页看图 → 解压最终 Overleaf 包后重新编译与复审。三轮都通过才算模板验收完成。
