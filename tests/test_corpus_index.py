# -*- coding: utf-8 -*-
"""test_corpus_index.py — papers_index.json 全量索引完整性测试。

覆盖：
  - 总数 729
  - 每条必填字段存在
  - paper_id 唯一
  - text_path 指向的抽文文件真实存在（抽文覆盖率）
  - year 在 2004-2024 范围
"""
import json
from pathlib import Path

import pytest

from conftest import CORPUS, REPO_ROOT

INDEX = CORPUS / "papers_index.json"
REQUIRED_FIELDS = ["paper_id", "year", "title", "text_path", "extract_status"]
# corpus/text 为本地生成的抽文产物（.gitignore 排除，不入库）
TEXT_ROOT = REPO_ROOT / "corpus" / "text"


@pytest.fixture(scope="module")
def index():
    assert INDEX.is_file(), f"索引文件不存在: {INDEX}"
    with open(INDEX, encoding="utf-8") as f:
        return json.load(f)


def test_total_729(index):
    assert index.get("total") == 729
    papers = index["papers"]
    assert len(papers) == 729, f"索引条数 {len(papers)} != 729"


def test_required_fields_present(index):
    missing = []
    for p in index["papers"]:
        for f in REQUIRED_FIELDS:
            if f not in p:
                missing.append((p.get("paper_id", "?"), f))
    assert not missing, f"缺必填字段的条目（前10）: {missing[:10]}"


def test_paper_id_unique(index):
    ids = [p["paper_id"] for p in index["papers"]]
    assert len(ids) == len(set(ids)), "存在重复 paper_id"


def test_year_range(index):
    bad = [p["paper_id"] for p in index["papers"]
           if not (2004 <= int(p["year"]) <= 2024)]
    assert not bad, f"year 越界条目: {bad[:10]}"


def test_text_path_contract_and_local_coverage(index):
    """便携安装检查索引契约；本地有全文抽文时再检查 729 篇覆盖率。"""
    paths = [Path(p["text_path"]) for p in index["papers"]]
    bad = [str(p) for p in paths
           if p.is_absolute() or ".." in p.parts
           or p.parts[:2] != ("corpus", "text") or p.suffix != ".txt"]
    assert not bad, f"text_path 越界或格式错误（前10）: {bad[:10]}"
    assert len(paths) == len(set(paths)), "存在重复 text_path"

    # 全文抽文因版权与体积不随 skill 分发；若本机明确装载，则必须一篇不少。
    if TEXT_ROOT.is_dir():
        missing = [str(p) for p in paths if not (REPO_ROOT / p).is_file()]
        assert not missing, f"抽文缺失 {len(missing)} 篇（前10）: {missing[:10]}"


def test_extract_status_ok(index):
    bad = [p["paper_id"] for p in index["papers"]
           if str(p.get("extract_status", "")).lower() not in ("ok",)]
    # 允许极少数抽文降级记录存在但需在 notes 标注；这里只统计 ok 比例
    ok_ratio = sum(1 for p in index["papers"]
                   if str(p.get("extract_status", "")).lower() == "ok") / len(index["papers"])
    assert ok_ratio >= 0.99, f"抽文 ok 比例过低: {ok_ratio:.2%}"
