# -*- coding: utf-8 -*-
"""pytest 公共夹具：定位仓库根、脚本目录、临时工作区。"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
CORPUS = REPO_ROOT / "corpus"
PLAYBOOKS = REPO_ROOT / "playbooks"
ASSETS = REPO_ROOT / "assets"

# 让 import 被测脚本成为可能（脚本不带包名，直接加入 sys.path）
for p in (str(SCRIPTS), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
