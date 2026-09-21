# quickstart demo · 工具链最小闭环样例（Wave5-C）

> 用一道**完全虚构**的单变量优化题，验证"题面 → 初始化 → 读题审计 → 原型匹配 →
> 技术路线图 → LaTeX 编译 PDF"的最小闭环。**不引用任何真实赛题语料**。

## 题目
某工厂生产产品 A，成本 $C(x)=x^2-10x+100$，售价固定 50，求利润最大的产量；
并评价成本二次项系数 $\pm10\%$ 时的鲁棒性。见 [`problem.txt`](problem.txt)。

**解析答案**（供对照，非工具产出）：标称 $a=1$ 时 $x^*=30$、$P^*=800$；
$a\in\{0.9,1.0,1.1\}$ 时 $x^*\approx\{33.3,30,27.3\}$、$P^*\approx\{900,800,718\}$。

## 一键复现
在**仓库根目录**执行：
```powershell
powershell -ExecutionPolicy Bypass -File scripts\quickstart_demo.ps1
```
脚本会打印每步进度，产物落到 `_work\quickstart_demo\`；最后一步（Step 7）跑自检闭环，
把《论文自检表_已勾选.md》拷回本目录作为闭环证据。

## 分步说明（手动版）
| 步 | 命令 | 预期 |
|---|---|---|
| 1 自检 | `python scripts\doctor.py` | 环境表，无 FAIL |
| 2 初始化 | `python scripts\contest_init.py --workdir _work\quickstart_demo` | 建好五区骨架 |
| 3 读题审计 | 见 [`read_audit_report.md`](read_audit_report.md)（桩示例） | 要素拆解+选型 |
| 4 原型匹配 | `python scripts\playbook_match.py --txt docs\examples\quickstart\problem.txt` | 命中 **optimization**（conf≈0.9） |
| 5 路线图 | `python scripts\render_roadmap.py --spec assets\roadmap\templates\optimization.yaml --outdir _work\quickstart_demo\roadmap` | 出 png/pdf/mmd/dot |
| 6 编译论文 | `cd docs\examples\quickstart; xelatex main.tex; xelatex main.tex` | 出 `main.pdf`，中文正常 |
| 7 自检闭环 | `python scripts\paper_checklist.py --tex main.tex --problems 1 --archetype optimization --outdir _work\quickstart_demo --strict` | 机检 0 ❌、人工条目全裁决、退出码 0 |

## 自检闭环（Step 7）
Step 7 在编译出 PDF 之后，对玩具论文跑 `scripts\paper_checklist.py`，把"机检 + 人工裁决"
闭环补齐，做到自检表 100% 闭环：

1. **拷入人工裁决 sidecar**：把本目录预置的 `paper_checklist_decisions.json` 拷到工作目录。
   该文件预填了所有必须人工裁决的条目（字体 F 系列、篇幅 L 系列、配色 T06、图是否合理 Q08、
   叙事 W 系列等）的结论——多数标 `pass`，面向其他题型（评价/预测/分类）的条目标 `na`。
2. **跑一次机检**：`paper_checklist.py` 对 `main.tex` 做可确定性检查（R/Q/S/H/B/A/E/V 系列），
   并读取 sidecar 渲染人工条目，输出《论文自检表_已勾选.md》。
3. **--strict 门禁**：再跑一次 `--strict`，要求退出码 0——即机检 0 个 ❌ 且所有人工条目均已裁决。
4. **闭环证据入库**：把工作目录里生成的《论文自检表_已勾选.md》拷回本目录。

**产物**：`paper_checklist_decisions.json`（人工裁决 sidecar）、`论文自检表_已勾选.md`（闭环证据）。

**如何验证**：重新运行 `scripts\quickstart_demo.ps1`，观察 Step 7 末尾打印
"`--strict` 通过（退出码 0）"，且本目录下 `论文自检表_已勾选.md` 存在、末尾统计行为
`✅ ...  ❌ 0  ☐ 0  ➖ ...`。

## 本目录产物
| 文件 | 说明 |
|---|---|
| `problem.txt` | 题面纯文本（供 playbook_match 读） |
| `problem.yaml` | 桩配置：模型/鲁棒性/管线步骤 |
| `read_audit_report.md` | 读题审计报告桩示例 |
| `main.tex` / `main.pdf` | 极简中文论文源 / 编译产物（含灵敏度分析小节） |
| `roadmap_optimization.yaml` | 技术路线图所用 optimization 模板 |
| `roadmap.png` / `roadmap.pdf` | 路线图渲染产物（Wave5-A 渲染器） |
| `paper_checklist_decisions.json` | Step 7 人工裁决 sidecar（预填全部 manual 条目） |
| `论文自检表_已勾选.md` | Step 7 生成的闭环证据（--strict 通过） |

## 说明与边界
- 第 5 步依赖 Wave5-A 的 `scripts/render_roadmap.py`；本仓库已就绪，若缺失脚本会打印"待就绪"并跳过。
- `build_latex.py` 面向完整论文模板（需 manifest + template-dir），本玩具样例按任务约定**手动 xelatex 编译极简 tex**，不跑完整模板链。
- 正式比赛请把本样例的桩内容替换为真实题面；本 quickstart 不调用 MATLAB，完整测试在检测到 MATLAB 时会自动执行真机烟雾测试。
