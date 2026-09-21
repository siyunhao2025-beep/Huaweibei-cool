#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
contest_init.py — 比赛日初始化工作目录骨架（Wave0）。

从 assets/scaffold/ 复制出比赛工作目录，按 config/contest.json 的路径约定建好
题目/数据/求解/论文/提交附件五区，并核对当届官方规则待确认位。

来源：演进自 v2.1 `比赛当天初始化.py` 与 `比赛当天_先读我.md`。
用法：
  python scripts/contest_init.py --help
  python scripts/contest_init.py --workdir ./_work/contest_2026
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = REPO_ROOT / "assets" / "scaffold"
CONTEST_JSON = REPO_ROOT / "config" / "contest.json"
CHECKLIST_MD = REPO_ROOT / "assets" / "checklists" / "优秀论文自检表.md"


def load_config() -> dict:
    if CONTEST_JSON.exists():
        return json.loads(CONTEST_JSON.read_text(encoding="utf-8"))
    return {}


def _copy_checklist(workdir: Path) -> None:
    """Wave6-A：把优秀论文自检表复制到工作目录的 论文/ 下。"""
    target_dir = workdir / "论文"
    target_dir.mkdir(parents=True, exist_ok=True)
    if CHECKLIST_MD.exists():
        shutil.copy2(CHECKLIST_MD, target_dir / CHECKLIST_MD.name)


def _copy_contest_config(workdir: Path) -> None:
    """Seed a per-contest config so user Figure/page decisions have one writable home."""
    if not CONTEST_JSON.is_file():
        return
    target = workdir / "config" / "contest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(CONTEST_JSON, target)


def init_workdir(workdir: Path) -> None:
    workdir.mkdir(parents=True, exist_ok=True)
    if SCAFFOLD.exists():
        for item in SCAFFOLD.iterdir():
            target = workdir / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
    else:
        # 兜底：直接建五区
        for name in ["题目", "数据/原始", "数据/中间", "求解", "论文", "提交附件"]:
            (workdir / name).mkdir(parents=True, exist_ok=True)
    _copy_checklist(workdir)
    _copy_contest_config(workdir)
    print(f"工作目录已初始化: {workdir}")


def main() -> None:
    ap = argparse.ArgumentParser(description="华为杯比赛日初始化工作目录骨架（Wave0）。")
    ap.add_argument("--workdir", default=str(REPO_ROOT / "_work" / "contest"),
                    help="工作目录路径，默认 _work/contest。")
    args = ap.parse_args()
    cfg = load_config()
    contest = cfg.get("contest", {})
    print("当前比赛配置核对位：")
    print(f"  届次: {contest.get('edition_cn', '待确认')}")
    print(f"  年份: {contest.get('year', '待确认')}")
    print(f"  官方规则已核对: {contest.get('verified_against_official_rules', False)}")
    print("  提示：比赛日先按官方通知核对届次/页数/格式，再进入求解。\n")
    init_workdir(Path(args.workdir).resolve())


if __name__ == "__main__":
    main()
