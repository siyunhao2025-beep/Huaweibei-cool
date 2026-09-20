# quickstart_demo.ps1 — 一键跑通玩具样例（Wave5-C）
# 用法（仓库根目录）：
#   powershell -ExecutionPolicy Bypass -File scripts\quickstart_demo.ps1
# 全程中文打印进度；不碰 Desktop 语料，只用内置虚构题。
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot   # scripts\ 的上一级 = 仓库根
Set-Location $repo
$demoDir = Join-Path $repo "docs\examples\quickstart"
$workDir = Join-Path $repo "_work\quickstart_demo"

function Step($i, $msg) { Write-Host "`n[$i] $msg" -ForegroundColor Cyan }

Step 1/6 "环境自检（doctor.py）"
python scripts\doctor.py

Step 2/6 "contest_init 初始化工作目录 -> $workDir"
python scripts\contest_init.py --workdir $workDir

Step 3/6 "读题审计报告（桩内容，直接拷贝示例）"
Copy-Item (Join-Path $demoDir "read_audit_report.md") (Join-Path $workDir "读题审计报告.md") -Force
Copy-Item (Join-Path $demoDir "problem.txt")            (Join-Path $workDir "problem.txt") -Force
Write-Host "  已写入 读题审计报告.md / problem.txt"

Step 4/6 "playbook_match 题面原型匹配（应命中 optimization）"
python scripts\playbook_match.py --txt (Join-Path $workDir "problem.txt")

Step 5/6 "技术路线图渲染（render_roadmap.py，optimization 模板）"
if (Test-Path "scripts\render_roadmap.py") {
    $roadmapSpec = Join-Path $repo "assets\roadmap\templates\optimization.yaml"
    $roadmapOut  = Join-Path $workDir "roadmap"
    python scripts\render_roadmap.py --spec $roadmapSpec --outdir $roadmapOut --fmt png,pdf
    if (Test-Path (Join-Path $roadmapOut "*.png")) {
        Write-Host "  路线图已渲染: $roadmapOut" -ForegroundColor Green
    }
} else {
    Write-Host "  [跳过] render_roadmap.py 尚未就绪（Wave5-A）。" -ForegroundColor Yellow
    Write-Host "  待技术路线图渲染器就绪后，对本题面跑一次即可。"
}

Step 6/6 "xelatex 编译极简论文 -> PDF"
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
}

Write-Host "`n=== quickstart demo 完成 ===" -ForegroundColor Cyan
Write-Host "产物：$workDir ；示例稿：$demoDir"
