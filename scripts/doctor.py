#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""doctor.py — 华为杯研赛 AI 作战中枢 一键环境自检（Wave5-C）。

逐项检查本机跑通本仓库所需的环境，每项给出 PASS / WARN / FAIL / SKIP、
详情与修复建议，最后汇总并给出修复清单。

用法：
  python scripts/doctor.py              # 人类可读的对齐表格
  python scripts/doctor.py --json        # 机器可读 JSON（供 tests/test_doctor.py 断言）
  python scripts/doctor.py --matlab-probe  # 额外做一次 matlab -batch version 快检（默认不跑，避免冷启动）
  python scripts/doctor.py --help

退出码：全部通过为 0；存在 FAIL 为 1；只有 WARN 为 0（不阻塞）。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# (import 名, 展示名, 是否必需) —— 与 requirements.txt 保持一致
REQUIRED_DEPS = [
    ("fitz", "pymupdf", True),       # fitz 是 pymupdf 的 import 名
    ("pypdf", "pypdf", True),
    ("docx", "python-docx", True),   # import 名 docx
    ("pytest", "pytest", True),
    ("matplotlib", "matplotlib", True),
    ("numpy", "numpy", True),
    ("pandas", "pandas", True),
    ("scipy", "scipy", False),        # 主要用于 MATLAB .mat 互操作
    ("yaml", "pyyaml", True),         # import 名 yaml
]

COMMON_MATLAB_ROOTS = [
    r"C:\Program Files\MATLAB",
    r"C:\Program Files (x86)\MATLAB",
    "/usr/local/MATLAB",
    "/Applications",
]

# 不弹窗的创建标志（Windows）
_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    """跑外部命令，返回 (退出码, 合并输出)。永不抛异常。"""
    try:
        p = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=_CREATE_NO_WINDOW,
        )
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        return p.returncode, out.strip()
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s: {' '.join(cmd)}"
    except Exception as e:  # noqa: BLE001 - doctor 必须永不崩
        return 1, f"error: {e}"


def check_python_version() -> dict:
    v = sys.version_info
    ok = (v.major, v.minor) >= (3, 10)
    return {
        "id": "python_version",
        "name": "Python 版本（≥3.10）",
        "status": "PASS" if ok else "FAIL",
        "detail": f"{v.major}.{v.minor}.{v.micro} ({sys.executable})",
        "fix": "" if ok else "安装 Python 3.10+；当前版本过旧，建议用 3.12 长期维护版。",
    }


def _try_import(dist: str) -> tuple[bool, str]:
    """按展示名尝试 import，返回 (成功, 版本)。pymupdf 优先用新 import 名。"""
    candidates = {
        "pymupdf": ["pymupdf", "fitz"],
        "python-docx": ["docx"],
        "pyyaml": ["yaml"],
    }.get(dist, [dist.replace("-", "_")])
    last_err = None
    for mod in candidates:
        try:
            m = __import__(mod)
            return True, getattr(m, "__version__", "?")
        except ImportError as e:  # noqa: PERF203
            last_err = e
    return False, str(last_err)


def check_deps() -> dict:
    rows = []
    missing = []
    for mod, dist, required in REQUIRED_DEPS:
        ok, ver = _try_import(dist)
        if ok:
            rows.append(f"{dist}=={ver}")
        else:
            missing.append(dist)
            rows.append(f"{dist}: MISSING")
    if missing:
        must = [dd for (_, dd, r) in REQUIRED_DEPS if r and dd in missing]
        status = "FAIL" if must else "WARN"
        fix = (f"pip install {' '.join(missing)}"
               + ("（scipy 仅 .mat 互操作用，缺失可暂不装）" if not must else ""))
    else:
        status = "PASS"
        fix = ""
    return {
        "id": "deps",
        "name": "Python 依赖",
        "status": status,
        "detail": "; ".join(rows),
        "fix": fix,
    }


def check_pytest() -> dict:
    rc, out = _run([sys.executable, "-m", "pytest", "--version"], timeout=30)
    first = out.splitlines()[0] if out else ""
    ok = rc == 0 and "pytest" in first.lower()
    return {
        "id": "pytest",
        "name": "pytest 可运行",
        "status": "PASS" if ok else "FAIL",
        "detail": first or out[:200],
        "fix": "" if ok else "pip install -U pytest",
    }


def check_git() -> dict:
    rc, out = _run(["git", "--version"], timeout=15)
    if rc != 0:
        return {
            "id": "git", "name": "git 可用",
            "status": "FAIL", "detail": out[:200],
            "fix": "安装 Git for Windows：https://git-scm.com/download/win",
        }
    rc2, http_proxy = _run(["git", "config", "--get", "http.proxy"], timeout=10)
    rc3, https_proxy = _run(["git", "config", "--get", "https.proxy"], timeout=10)
    proxy = (http_proxy or https_proxy).strip()
    detail = out.splitlines()[0]
    if proxy:
        status = "PASS"
        detail += f"；已配置代理 {proxy}"
        fix = ""
    else:
        status = "WARN"
        detail += "；未配置 http(s).proxy"
        fix = ("GitHub 直连可能不稳定，可设代理 127.0.0.1:7897："
               "git config --global http.proxy http://127.0.0.1:7897 && "
               "git config --global https.proxy http://127.0.0.1:7897")
    return {"id": "git", "name": "git 可用 + 代理", "status": status,
            "detail": detail, "fix": fix}


def check_xelatex() -> dict:
    rc, out = _run(["xelatex", "--version"], timeout=30)
    if rc != 0:
        return {
            "id": "xelatex", "name": "xelatex 可用",
            "status": "FAIL", "detail": out[:200] or "xelatex 不在 PATH",
            "fix": "安装 TeX Live 并勾选 xetex；或安装 MiKTeX 后加 xelatex 到 PATH。",
        }
    first = out.splitlines()[0] if out else "xelatex"
    # 中文字体：用 matplotlib 的字体管理器做跨平台代理检测
    cn = _detect_cn_fonts()
    if cn["yahei"] or cn["simhei"] or cn["stxinwei"]:
        fonts_ok = []
        if cn["yahei"]:
            fonts_ok.append("Microsoft YaHei")
        if cn["simhei"]:
            fonts_ok.append("SimHei")
        if cn["stxinwei"]:
            fonts_ok.append("STXinwei")
        status = "PASS"
        detail = f"{first}；中文字体: {', '.join(fonts_ok)}"
        fix = ""
    else:
        status = "WARN"
        detail = f"{first}；未检测到 YaHei/SimHei/STXinwei"
        fix = "安装中文字体（如 Microsoft YaHei / SimHei / 思源宋体），否则 xelatex 中文会回退或缺字。"
    return {"id": "xelatex", "name": "xelatex + 中文字体", "status": status,
            "detail": detail, "fix": fix}


def _detect_cn_fonts() -> dict:
    """用 matplotlib.font_manager 检测中文字体（跨平台）。"""
    res = {"yahei": False, "simhei": False, "stxinwei": False}
    try:
        import matplotlib.font_manager as fm
        names = {f.name for f in fm.fontManager.ttflist}
        res["yahei"] = any("YaHei" in n for n in names)
        res["simhei"] = any(n == "SimHei" for n in names)
        res["stxinwei"] = any("STXinwei" in n or "Xinwei" in n for n in names)
    except Exception:  # noqa: BLE001
        pass
    return res


def check_cn_font_matplotlib() -> dict:
    cn = _detect_cn_fonts()
    if cn["yahei"] or cn["simhei"]:
        which = []
        if cn["yahei"]:
            which.append("YaHei")
        if cn["simhei"]:
            which.append("SimHei")
        return {"id": "matplotlib_cn_font", "name": "matplotlib 中文字体",
                "status": "PASS", "detail": "检测到 " + "/".join(which), "fix": ""}
    return {
        "id": "matplotlib_cn_font", "name": "matplotlib 中文字体",
        "status": "WARN",
        "detail": "未检测到 YaHei/SimHei；matplotlib 中文图可能出豆腐块",
        "fix": "安装中文字体并清缓存：rm -rf ~/.cache/matplotlib；测试中请用字体回退逻辑，不要因缺字体让 CI 失败。",
    }


def find_matlab() -> str | None:
    exe = shutil.which("matlab")
    if exe:
        return exe
    for root in COMMON_MATLAB_ROOTS:
        p = Path(root)
        if not p.is_dir():
            continue
        for pattern in ("R*/bin/matlab.exe", "R*/bin/glnxa64/MATLAB"):
            cands = sorted(p.glob(pattern), reverse=True)
            if cands:
                return str(cands[0])
    return None


def check_matlab(probe: bool) -> dict:
    exe = find_matlab()
    if exe is None:
        return {
            "id": "matlab", "name": "MATLAB 路径",
            "status": "WARN",
            "detail": "未在常见路径/PATH 找到 matlab.exe",
            "fix": ("若需 MATLAB 求解，安装 R2023b+ 并把 bin 加入 PATH；"
                    "纯 Python 链可不装（MATLAB 用例在 pytest 中默认 skip）。"),
        }
    detail = f"找到 {exe}"
    if not probe:
        return {
            "id": "matlab", "name": "MATLAB 路径",
            "status": "PASS", "detail": detail + "（未做 -batch 快检，加 --matlab-probe 可快检）",
            "fix": "",
        }
    # 可选 -batch 快检：只跑 version，30s 超时；不碰用户正在跑的进程（-batch 是独立进程）
    rc, out = _run([exe, "-batch", "disp(version)"], timeout=30)
    if rc == 0:
        ver = next((ln.strip() for ln in out.splitlines() if ln.strip()), "")
        return {"id": "matlab", "name": "MATLAB 路径 + -batch 快检",
                "status": "PASS", "detail": f"{exe}；version={ver}", "fix": ""}
    if rc == 124:
        return {"id": "matlab", "name": "MATLAB 路径 + -batch 快检",
                "status": "WARN",
                "detail": f"{exe}；-batch version 30s 超时（冷启动/license 争抢，常见现象）",
                "fix": "确认无其它 MATLAB 占满 license 后重试；超时不代表安装损坏。"}
    return {"id": "matlab", "name": "MATLAB 路径 + -batch 快检",
            "status": "WARN", "detail": f"{exe}；-batch 返回 {rc}: {out[:200]}",
            "fix": "检查 license 服务 / 不要用 -r，改用 -batch。"}


def check_word_com() -> dict:
    if sys.platform != "win32":
        return {"id": "word_com", "name": "Word COM（docx 渲染）",
                "status": "SKIP", "detail": "非 Windows，跳过", "fix": ""}
    # 只查 ProgID 是否已注册，不启动 Word（启动慢且可能弹窗）
    rc, out = _run(
        ["powershell", "-NoProfile", "-Command",
         "if (Test-Path 'Registry::HKEY_CLASSES_ROOT\\Word.Application') { 'registered' } else { 'missing' }"],
        timeout=20,
    )
    if rc == 0 and "registered" in out:
        return {"id": "word_com", "name": "Word COM（docx 渲染）",
                "status": "PASS",
                "detail": "Word.Application ProgID 已注册（可 New-Object -ComObject Word.Application）",
                "fix": ""}
    return {"id": "word_com", "name": "Word COM（docx 渲染）",
            "status": "WARN",
            "detail": "未找到 Word.Application ProgID",
            "fix": "安装 Microsoft Word；仅做 docx 读写（python-docx）可不装，渲染 PDF 才需要。"}


def check_graphviz() -> dict:
    rc, out = _run(["dot", "-V"], timeout=10)
    if rc == 0 or (rc != 127 and out):
        first = out.splitlines()[0] if out else "dot"
        return {"id": "graphviz", "name": "graphviz dot（可选 .dot 渲染）",
                "status": "PASS", "detail": first, "fix": ""}
    return {"id": "graphviz", "name": "graphviz dot（可选 .dot 渲染）",
            "status": "WARN",
            "detail": "dot 不在 PATH（可选依赖，仅用于把 .dot 渲染成图）",
            "fix": "安装 graphviz：winget install Graphviz.Graphviz，并把 bin 加入 PATH。",
            }


def run_all(matlab_probe: bool) -> list[dict]:
    return [
        check_python_version(),
        check_deps(),
        check_pytest(),
        check_git(),
        check_xelatex(),
        check_cn_font_matplotlib(),
        check_matlab(matlab_probe),
        check_word_com(),
        check_graphviz(),
    ]


def summarize(checks: list[dict]) -> dict:
    cnt = {"PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0}
    for c in checks:
        cnt[c["status"]] = cnt.get(c["status"], 0) + 1
    return {"pass": cnt["PASS"], "warn": cnt["WARN"], "fail": cnt["FAIL"],
            "skip": cnt["SKIP"], "total": len(checks)}


def render_table(checks: list[dict], summ: dict) -> str:
    lines = []
    lines.append("=" * 78)
    lines.append("华为杯研赛 AI 作战中枢 · 环境自检（scripts/doctor.py）")
    lines.append("=" * 78)
    header = f"{'状态':<5} {'检查项':<28} {'详情'}"
    lines.append(header)
    lines.append("-" * 78)
    for c in checks:
        detail = c["detail"].replace("\n", " ")
        if len(detail) > 60:
            detail = detail[:57] + "..."
        lines.append(f"{c['status']:<5} {c['name']:<28} {detail}")
    lines.append("-" * 78)
    lines.append(f"汇总：{summ['pass']} PASS / {summ['warn']} WARN / "
                 f"{summ['fail']} FAIL / {summ['skip']} SKIP（共 {summ['total']} 项）")
    fixes = [c for c in checks if c["fix"]]
    if fixes:
        lines.append("")
        lines.append("修复建议清单：")
        for c in fixes:
            lines.append(f"  [{c['status']}] {c['name']}")
            lines.append(f"       → {c['fix']}")
    else:
        lines.append("全部通过，无需修复。")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="华为杯研赛 AI 作战中枢 一键环境自检。")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出（供测试断言）")
    ap.add_argument("--matlab-probe", action="store_true",
                    help="额外跑一次 matlab -batch version 快检（默认不跑，避免冷启动）")
    args = ap.parse_args(argv)

    checks = run_all(args.matlab_probe)
    summ = summarize(checks)

    if args.json:
        print(json.dumps({"summary": summ, "checks": checks},
                         ensure_ascii=False, indent=2))
    else:
        print(render_table(checks, summ))

    return 1 if summ["fail"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
