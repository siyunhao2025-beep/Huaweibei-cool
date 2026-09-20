# TROUBLESHOOTING.md · 常见问题排查手册（Wave5-C）

> 适用范围：Windows + PowerShell 5.1 + Python 链。每条按 **现象 → 原因 → 解决步骤 → 验证方法** 给出。
> 跑前先做一遍环境自检：`python scripts/doctor.py`，它会告诉你哪些项是 WARN/FAIL。

---

## 0. 先跑环境自检（一切从这里开始）

```powershell
python scripts/doctor.py            # 人读表格
python scripts/doctor.py --json     # 机读，供 CI / 断言
```

- 出现 `FAIL`：按表格"修复建议清单"逐条处理。
- 只有 `WARN`：不阻塞，但记录下来（常见：graphviz 未装、MATLAB -batch 冷启动超时）。

---

## 1. PowerShell 5.1 编码坑（中文乱码 / 引号 / Tee-Object）

### 1.1 现象：脚本里的中文输出成 `����`，或写出的 .py/.json 打开是乱码

**原因**：PowerShell 5.1 的默认输出编码是 OEM/GBK（代码页 936），且 `Out-File` / `>` 不带 BOM；而 Python 3.15+ 默认按 UTF-8 读源文件，BOM 处理不一致。

**解决步骤**：
1. 所有交给 Python 读的文本文件，统一用 **UTF-8 with BOM**（记事本"另存为"选 UTF-8；VS Code 右下角选 `UTF-8 with BOM`）。Python 端读文件统一 `encoding="utf-8-sig"`（本仓库 `playbook_match.py` 就是这么读的）。
2. PowerShell 命令行先切 UTF-8 代码页：
   ```powershell
   chcp 65001
   $OutputEncoding = [System.Text.Encoding]::UTF8
   [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
   ```
3. 重定向输出到日志时，用 `cmd /c "... > file.log 2>&1"`，不要直接用 PowerShell 的 `>`（见 §4.4）。

**验证方法**：`python -c "print('中文测试')"` 不再出乱码；写一个含中文的 .py，`python 文件.py` 输出正常。

### 1.2 现象：`Tee-Object -Encoding utf8` 报错"无法找到参数"

**原因**：Windows PowerShell **5.1** 的 `Tee-Object` 没有 `-Encoding` 参数（PS 7+ 才有）。

**解决步骤**：
- 不要用 `Tee-Object -Encoding utf8`。改用：
  ```powershell
  python xxx.py 2>&1 | Tee-Object -FilePath run.log
  ```
  或直接 `cmd /c "python xxx.py > run.log 2>&1"`。

**验证方法**：命令不再报参数错误，`run.log` 存在且非 0 字节。

### 1.3 现象：一行里带中文路径/引号的命令报"字符串缺少终止符"

**原因**：PowerShell 5.1 内联引号转义规则与 cmd 不同；`"` 内嵌双引号要写成 `""` 或 `` `" ``。

**解决步骤**：
- 调 MATLAB 时（见 `modules/matlab-conventions.md` §2.1）：
  ```powershell
  cmd /c '"C:\Program Files\MATLAB\R2024b\bin\matlab.exe" -batch "run(''scripts\matlab_smoke.m'')" > out.log 2>&1'
  ```
  即：外层单引号包整串，内层 `''` 转义单引号。
- 复杂命令写进 `.ps1` 文件用 here-string，不要在一行里硬塞。

**验证方法**：脚本可无报错执行，产物落盘。

---

## 2. git 代理 7897（GitHub push/pull 不稳定）

### 2.1 现象：`git push` / `git pull` 卡住、超时或报 Failed to connect

**原因**：本机走本地代理（Clash/v2ray 等，端口 7897），git 没读系统代理，默认直连 GitHub。

**设置代理**：
```powershell
git config --global http.proxy  http://127.0.0.1:7897
git config --global https.proxy http://127.0.0.1:7897
```

**取消代理**（换网络/离线时）：
```powershell
git config --global --unset http.proxy
git config --global --unset https.proxy
```

**排查端口是否真的在监听**：
```powershell
netstat -ano | findstr 7897          # 应看到 127.0.0.1:7897 LISTENING
Test-NetConnection 127.0.0.1 -Port 7897   # TcpTestSucceeded = True 才通
```

### 2.2 现象：配了代理还是 push 失败

**原因**：代理软件没开 / 端口不是 7897 / 只设了 http 没设 https。

**解决步骤**：
1. `netstat -ano | findstr 7897` 确认端口在听；不在听就去开代理软件。
2. 确认两边都设了：`git config --get http.proxy; git config --get https.proxy`。
3. 临时单条命令带代理测试：`git -c http.proxy=http://127.0.0.1:7897 ls-remote origin`。
4. 若公司网络要求别的端口，把 7897 换成实际端口（如 7890/10809）。

**验证方法**：`git ls-remote origin` 秒回；`python scripts/doctor.py` 的 git 项显示"已配置代理"。

---

## 3. xelatex 字体问题（STXinwei 缺失 / 中文回退）

### 3.1 现象：`xelatex` 编译中文论文报 `fontspec` 错，或中文出方块/缺字

**原因**：模板指定的中文字体（如 `STXinwei`/"华文新魏"）本机没有；xelatex 默认字体不含中文。

**解决步骤**：
1. 先自检：`python scripts/doctor.py` 看"xelatex + 中文字体"项。
2. 本机常见可用字体：`Microsoft YaHei`（微软雅黑，必装）、`SimHei`（黑体）。`STXinwei` 只在装有"华文新魏"的机器上才有（`C:\Windows\Fonts\STXINWEI.TTF`）。
3. 把 tex 里的 `\setCJKmainfont{...}` 改成本机存在的字体：
   ```latex
   \setCJKmainfont{Microsoft YaHei}   % 或 SimHei；不要写 STXinwei 除非它确实在
   ```
4. 找不到字体时查本机列表：`fc-list :lang=zh`（TeX Live）或 `Get-ChildItem C:\Windows\Fonts`。

> 历史说明：旧模板曾因引用不存在的 `loglo.png`（日志图占位）导致编译失败，**该缺陷已在 Wave 早期修复**；现在若再报缺图，先 `ls 论文/` 确认图片真的生成了，而不是复制旧占位名。

**验证方法**：`xelatex -interaction=nonstopmode main.tex` 退出码 0，打开 PDF 中文清晰无方块。

### 3.2 现象：第一次编译过了，第二次字体缓存报错

**解决**：清 xelatex 辅助文件后重编：`Remove-Item *.aux,*.log,*.out,*.toc -ErrorAction SilentlyContinue; xelatex main.tex`。

---

## 4. MATLAB -batch 调用（license / 线程 / 与用户进程共存 / 0 字节日志）

> 铁律：**不要 kill / attach 用户正在跑的 MATLAB**。真机验证一律另起 `matlab -batch` 独立进程，脚本头 `maxNumCompThreads(2);`，只跑一次。详见 `modules/matlab-conventions.md`。

### 4.1 现象：`matlab -batch` 报 License checkout failed / 等待 license

**原因**：机器上常驻交互式 MATLAB 占着 license；或 license 服务器不可达。

**解决步骤**：
1. 先看是不是用户进程占着：`Get-Process MATLAB`（只读查看，**不要 Stop-Process**）。
2. 等当前长任务跑完再试；**不要并发起第二个 -batch**。
3. 网络 license：确认 VPN / license server 通；本机 Designated Computer 许可则别同时开太多实例。

**验证**：`matlab -batch "disp(version)"` 能打印版本号。

### 4.2 现象：MATLAB 跑起来把 CPU 占满，风扇狂转

**原因**：脚本没限线程。

**解决步骤**：脚本第一行有效代码必须 `maxNumCompThreads(2);`（本仓库 `scripts/matlab_smoke.m` 已带）。含随机性的求解器（ga 等）再加 `rng(seed);` 保证可复现。

### 4.3 现象：跑 -batch 会不会影响用户已开的 MATLAB？

**结论**：不会互相侵入。`-batch` 是独立无界面进程，不连用户桌面会话。但它会和用户进程**抢 CPU / license**——所以才要 `maxNumCompThreads(2)`、只跑一次、冷启动慢要耐心等。

### 4.4 现象：重定向出来的日志是 0 字节

**原因**：PowerShell 5.1 直接 `> log.txt` 对原生命令的 stdout 缓冲/编码处理异常，或路径不存在。

**解决步骤**：用 `cmd /c` 包裹（cmd 语义的 `>` 最稳）：
```powershell
cmd /c '"C:\Program Files\MATLAB\R2024b\bin\matlab.exe" -batch "run(''scripts\matlab_smoke.m'')" > tests\fixtures\matlab_smoke_R2024b.log 2>&1'
```
- 确认目标目录存在（`tests\fixtures\` 已在仓库里）。
- 跑完立刻 `Get-Item log` 看 Length；0 字节通常是命令根本没执行成功，先去掉重定向在前台跑一遍看报错。

> 注意：日志里的中文可能显示成乱码（cmd 代码页伪影），**这不是字体坏了**——判断中文字体要看导出的 PNG，不要看控制台日志（见 `matlab-conventions.md` §4.2）。

---

## 5. venv / 依赖安装（Python 3.14 兼容性 / pip 源 / 锁版本）

### 5.1 现象：`pip install -r requirements.txt` 卡住或下不动

**原因**：PyPI 直连慢。

**解决步骤**：配国内镜像并建虚拟环境：
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 5.2 现象：Python 3.14 上某个包装不上

**说明**：本机实测 Python **3.14.7** 可装齐本仓库全部依赖（pymupdf/pypdf/python-docx/pytest/matplotlib/numpy/pandas/scipy/pyyaml 均有可用轮子）。但为了 CI 与他人机器稳定，**CI 统一用 Python 3.12**（兼容性最稳）。

**解决步骤**：
- 本机 3.14 能跑就用本机；要复现 CI 行为就装个 3.12。
- 某个包在新 Python 上没轮子时：先升级 pip（`python -m pip install -U pip`）再装；还不行就降到 requirements.txt 里钉住的最低版本。

### 5.3 现象：别人机器装完版本和我不一样，结果对不上

**原因**：requirements.txt 是 `>=` 下限，没锁死。

**解决**：要严格复现就补一份锁版本记录（`pip freeze > requirements-lock.txt`）；本仓库 `requirements.txt` 注明每个包的实测版本与必需/可选（见文件头注释），scipy 仅用于 MATLAB `.mat` 互操作，可不装。

---

## 6. pytest 失败排查

### 6.1 现象：`test_matlab_smoke_*` 在我这台没装 MATLAB 的机器上 fail

**预期行为**：**它本来就该 skip，不是 fail**。
- 找不到 `matlab.exe` → skip；
- 没设环境变量 `HUAWEI_RUN_MATLAB=1` → skip。
- 真机复跑：`$env:HUAWEI_RUN_MATLAB=1; python -m pytest tests/test_matlab_smoke.py -v`。

### 6.2 现象：深卡（corpus_cards / 视觉计划 schema）报 JSON schema 违例

**说明**：历史上深卡 schema 违例问题**已在 Wave4 修复**（盲调 30 题金标 + match_rules 调优到 97%）。现在若再报 schema 错：
1. 确认用的是仓库自带 `scripts/视觉计划.schema.json`，不要拿旧模板。
2. `python scripts/corpus_cards.py --help` 看是否最新；坏卡单独修，不要整批重跑覆盖金标。

### 6.3 现象：测试在中文路径下收集失败 / 文件找不到

**原因**：路径含中文/空格时，原生 Windows 编码或相对路径解析出问题。

**解决步骤**：
- 把仓库放在无中文无空格的路径（如 `C:\repos\Huaweibei-cool`）。
- 脚本内一律用 `Path(__file__).resolve()` 反推仓库根，不写死相对路径（本仓库脚本已这么做）。
- pytest 输出乱码：`set PYTHONUTF8=1` 或 `chcp 65001` 后再跑。

### 6.4 现象：matplotlib 在 CI（无中文字体）报缺字体

**预期行为**：应当**优雅回退而不是 fail**。测试里若用到中文图，先 `doctor.py` 式检测字体，无字体就跳过/回退英文标注。CI 配置见 `.github/workflows/ci.yml`。

**验证**：`python -m pytest tests/ -v` 全绿（MATLAB 相关显示 skip 属正常）。

---

## 速查表

| 现象 | 先做 |
|---|---|
| 不知道哪坏了 | `python scripts/doctor.py` |
| 中文乱码 | `chcp 65001` + 文件存 UTF-8 with BOM |
| git push 失败 | `netstat -ano \| findstr 7897`，再 `git config --global http.proxy ...` |
| xelatex 中文缺字 | 把字体改成 `Microsoft YaHei` |
| MATLAB license/0 字节日志 | `cmd /c "... > log 2>&1"`，别并发起第二个 |
| pytest 红 | 看是不是 MATLAB 用例在 skip（正常）；中文路径就换目录 |
