# quickstart_demo.ps1 — 一键跑通玩具样例（Wave5-C / Wave6.1 自检闭环）
# 用法（仓库根目录）：
#   powershell -ExecutionPolicy Bypass -File scripts\quickstart_demo.ps1
# 全程中文打印进度；不碰 Desktop 语料，只用内置虚构题。
# Step 7 跑 paper_checklist.py 自检闭环：机检 0 错 + 人工裁决 sidecar + --strict 退出 0。
$ErrorActionPreference = "Stop"
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom
$env:PYTHONUTF8 = "1"
$repo = Split-Path -Parent $PSScriptRoot   # scripts\ 的上一级 = 仓库根
Set-Location $repo
$demoDir = Join-Path $repo "docs\examples\quickstart"
$workDir = Join-Path $repo "_work\quickstart_demo"

function Step($i, $msg) { Write-Host "`n[$i] $msg" -ForegroundColor Cyan }

Step 1/7 "环境自检（doctor.py）"
python scripts\doctor.py

Step 2/7 "contest_init 初始化工作目录 -> $workDir"
python scripts\contest_init.py --workdir $workDir

Step 3/7 "读题审计报告（桩内容，直接拷贝示例）"
Copy-Item (Join-Path $demoDir "read_audit_report.md") (Join-Path $workDir "读题审计报告.md") -Force
Copy-Item (Join-Path $demoDir "problem.txt")            (Join-Path $workDir "problem.txt") -Force
Write-Host "  已写入 读题审计报告.md / problem.txt"

Step 4/7 "playbook_match 题面原型匹配（应命中 optimization）"
python scripts\playbook_match.py --txt (Join-Path $workDir "problem.txt")

Step 5/7 "技术路线图渲染（render_roadmap.py，optimization 模板）"
if (Test-Path "scripts\render_roadmap.py") {
    $roadmapSpec = Join-Path $repo "assets\roadmap\templates\optimization.yaml"
    $roadmapOut  = Join-Path $workDir "roadmap"
    python scripts\render_roadmap.py --spec $roadmapSpec --outdir $roadmapOut --fmt png,pdf
    if (Test-Path (Join-Path $roadmapOut "*.png")) {
        Write-Host "  路线图已渲染: $roadmapOut" -ForegroundColor Green
    }
} else {
    Write-Host "  [跳过] render_roadmap.py 尚未就绪。" -ForegroundColor Yellow
}

Step 6/7 "xelatex 编译极简论文 -> PDF"
$texSrc = Join-Path $demoDir "main.tex"
$texWork = Join-Path $workDir "main.tex"
Copy-Item $texSrc $texWork -Force
Push-Location $workDir
xelatex -interaction=nonstopmode main.tex > $null 2>&1
xelatex -interaction=nonstopmode main.tex > $null 2>&1
Pop-Location
if (Test-Path (Join-Path $workDir "main.pdf")) {
    $pdf = Get-Item (Join-Path $workDir "main.pdf")
    Write-Host ("  编译成功: {0} ({1:N0} bytes)" -f $pdf.FullName, $pdf.Length) -ForegroundColor Green
} else {
    Write-Host "  编译失败：请在 $workDir 手动跑 xelatex main.tex 看报错" -ForegroundColor Red
    exit 1
}

# --------------------------------------------------------------------------- #
# Step 7：自检闭环（Wave6.1）
#   7a. 把预置人工裁决 sidecar 拷进工作目录
#   7b. 跑 paper_checklist.py（机检 + 读 sidecar 裁决人工条目）
#   7c. 再跑 --strict，必须退出码 0（机检 0 错 + 人工条目全部裁决）
#   7d. 把生成的《论文自检表_已勾选.md》拷回 demoDir 作为闭环证据
# --------------------------------------------------------------------------- #
Step 7/7 "自检闭环（paper_checklist.py + 人工裁决 sidecar + --strict）"

# 玩具题实际为 1 个小问（求最优产量 + 评价鲁棒性），题型 optimization
$problems = 1
$decSrc   = Join-Path $demoDir "paper_checklist_decisions.json"
$decDst   = Join-Path $workDir "paper_checklist_decisions.json"
if (-not (Test-Path $decSrc)) {
    Write-Host "  [失败] 未找到预置人工裁决 sidecar：$decSrc" -ForegroundColor Red
    exit 1
}
Copy-Item $decSrc $decDst -Force
Write-Host "  7a 已拷入人工裁决 sidecar -> $decDst"

Write-Host "  7b 运行 paper_checklist.py（机检 + 人工裁决）..."
python scripts\paper_checklist.py --tex $texWork --problems $problems `
    --archetype optimization --outdir $workDir
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [失败] paper_checklist 机检未通过（存在 ❌），退出码 $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

Write-Host "  7c 运行 paper_checklist.py --strict（门禁：机检 0 错 + 人工全裁决）..."
python scripts\paper_checklist.py --tex $texWork --problems $problems `
    --archetype optimization --outdir $workDir --strict
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [失败] --strict 未通过：仍有 ❌ 或未裁决人工条目，退出码 $LASTEXITCODE" -ForegroundColor Red
    exit 1
}
Write-Host "  7c --strict 通过（退出码 0）" -ForegroundColor Green

$checkedSrc = Join-Path $workDir "论文自检表_已勾选.md"
$checkedDst = Join-Path $demoDir "论文自检表_已勾选.md"
if (Test-Path $checkedSrc) {
    Copy-Item $checkedSrc $checkedDst -Force
    Write-Host "  7d 闭环证据已入库 -> $checkedDst" -ForegroundColor Green
} else {
    Write-Host "  [失败] 未生成 $checkedSrc" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== quickstart demo 完成（含自检闭环）===" -ForegroundColor Cyan
Write-Host "产物：$workDir ；示例稿与闭环证据：$demoDir"
